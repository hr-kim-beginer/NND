from _03_control import cl_control_X
import utility
import math
import numpy as np
import header
import data_memory as dm
from collections import deque
import utility
import status_code
from _02_class_function import cl_timer

class Control_X_Mold(cl_control_X.Control_X):

    # ㅊㅇㅇ - input : NOTCH class 인스턴스, VISION class 인스턴스
    # ↑ return : 보정값
    def run(self, data_plc, data_vision):

        try:
            # 자동보정 로직 실행 여부 체크 (PLC 데이터 마지막 행 기준이라서 index -1로 지정)    
            if (data_plc.x_button== 1) and (data_plc.electrode_break_mode== 0):

                # 연속구간/재료교체구간 구분
                # ㅊㅇㅇ - 0: 시작 / 1: 연속구간 / 2: 재료교체구간 / 3: 재료교체 단차 지나감
                self.check_section(data_plc=data_plc, data_vision=data_vision)

                # 1. vision data for문 돌려서, 사용 가능한 데이터는 append할 것임.
                for seq in range(len(data_vision.I_cell_no)):

                    d_no = data_vision.I_cell_no[seq][0]
                    d_TP = data_vision.I_roi_mean_pitch[seq][0]

                    # 3. 현재-이전 값 차이 계산 (치수 데이터와 Cell no)
                    self.diff_pitch = d_TP - self.pre_TP
                    self.diff_no = d_no - self.pre_val_no

                    # 다음 데이터와의 비교를 위한 이전값 갱신
                    self.pre_TP = d_TP
                    self.pre_val_no = d_no

                    # Pitch보정은 Cell No 기반 계산이므로 Cell No가 초기화되면, data queue reset 필요.
                    if (d_no < 0)  or (self.diff_no < 0):
                         self.clear_queue()

                    # 4. 현재-이전 값 차이가 0이 아니고, 특정값 이내인지 체크
                    # (USL-LSL)의미 : 연속공정의 특성 상, 이전 Cell과의 데이터가 (USL-LSL) 정도의 큰 변화를 보이기 힘듬 → 오측 판단
                    if (self.diff_no != 0) and (abs(self.diff_pitch) > 0) and (abs(self.diff_pitch) < (self.usl_TP-self.lsl_TP)*2):

                        # 5. 현재 데이터가 gathering 허용 범위 내에 있는지 체크
                        if (d_TP < (self.usl_TP+self.tolerance)) and (d_TP > (self.lsl_TP-self.tolerance)):  

                            # 6. 사용 가능한 데이터 수집
                            self.qCELLNO.append(d_no)
                            self.qTP.append(d_TP)

                
                # 수집한 데이터가 제어주기 이상 쌓이면, 자동보정 offset 계산 시작
                if (len(self.qTP) >= self.control_cycle) and (self.chk_section != 2):

                    # queue에서 꺼낸 뒤, mold cavity 숫자에 맞춰 그룹핑
                    idx_start = self.qCELLNO.popleft()      # 첫번째 시작하는 데이터 Cell No를 기준으로 0부터 시작.
                    list_pitch = [self.qTP.popleft()]    # 첫번째 데이터 넣고 시작.

                    # 위에서 한개 꺼냈으므로 (control_cycle-1)개만큼 더 꺼내면 됨.
                    for n in range(self.control_cycle-1):
                        diff_idx = self.qCELLNO.popleft()-idx_start # 꺼낸 데이터와 시작 데이터 차이 계산

                        # idx 차이가 1 → 데이터를 놓치지 않았으므로, 바로 list에 추가
                        # idx 차이가 2이상 → 데이터를 놓침, 순번 유지를 위해 놓친 데이터는 ref값으로 대체하여 list에 추가
                        for k in range(diff_idx, 0, -1): # ㅊㅇㅇ - 놓친 index를 전부 ref값으로 넣어줘야 하기 때문에 diff_idx가 0이 될때까지 for문을 돌림
                            if k == 1:
                                list_pitch.append(self.qTP.popleft())
                            else:
                                list_pitch.append(self.ref_TP)
                                
                        idx_start += diff_idx

                    # pitch 데이터를 순번에 맞게 정리하는 과정에서 데이터 수가 늘어날 경우 대비 → cavity별 데이터 개수 같도록 자름.
                    num_group = len(list_pitch)//self.cavity_num
                    list_pitch_cut = list_pitch[0:num_group*self.cavity_num]

                    # 분산 계산을 위한 변수 선언 및 초기화 (금형 cavity의 최대 개수인 5개로 배열 설정)
                    sum = [0,0,0,0,0]
                    sump = [0,0,0,0,0]
                    pvar = [0,0,0,0,0]
                    pvargap = [1,1,1,1,1]

                    # 분산 계산
                    for i, d in enumerate(list_pitch_cut):
                        sum[i % self.cavity_num] += d
                        sump[i % self.cavity_num] += math.pow(d,2)
                    for p in range(self.cavity_num):
                        pvar[p] = (sump[p] / num_group) - math.pow((sum[p] / num_group), 2)
                        
                    
                    # 분산이 가장 큰 cavity group 선정
                    pvar_max_idx = pvar.index(max(pvar))
                    # 각 cavity group의 분산값과 max값과의 차이값 계산 (가장 작은 분산차를 찾기 위함)
                    for g in range(self.cavity_num):
                        if (g != pvar_max_idx):
                            pvargap[g] = abs(pvar[pvar_max_idx] - pvar[g])  # index가 같으면 초기값 1 유지.

                    # 찾은 idx가 현재 cavity 수를 넘는지 체크, 분산차의 최소값이 기준값을 넘는지 체크
                    utility.log_write(f"pvargap : {pvargap}")
                    
                    if (pvar_max_idx < self.cavity_num) and (min(pvargap) > self.pvar_criteria):    # pvar_criteria : 0.001

                        # 자동보정 Offset = Error(SPEC REF - 찾은 cavity 데이터 평균치) * gain
                        self.result_offset = (self.ref_TP - (sum[pvar_max_idx]/num_group)) * self.pgain

                        # 1회 보정량 상/하한치 조정
                        if (self.result_offset < -self.limit): self.result_offset = -self.limit
                        if (self.result_offset > self.limit): self.result_offset = self.limit
                        
                        self.control_count += 1  # 자동보정 카운트

                        return {"TP" : round(self.result_offset, 3)}

            elif (data_plc.electrode_break_mode == 1):
                self.clear_queue()
                
            else:
                self.clear_queue()

            return {}

        except Exception as ex:
            message = "Control_X_Mold Error"
            utility.log_write(f"Control_X_Mold Error : {ex}")
            utility.alarm_code_refresh(msg=message, err_code=status_code.X_Axis_Auto_Logic_Alarm)