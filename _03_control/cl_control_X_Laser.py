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

class Control_X_Laser(cl_control_X.Control_X):

    # ㅊㅇㅇ - input : NOTCH class 인스턴스, VISION class 인스턴스
    # ↑ return : 보정값
    def run(self, data_plc, data_vision):

        try:
            # 자동보정 로직 실행 여부 체크 (PLC 데이터 마지막 행 기준이라서 index -1로 지정)    
            if (data_plc.x_button== 1) and (data_plc.electrode_break_mode== 0):

                # 연속구간/재료교체구간 구분
                # ㅊㅇㅇ - 0: 시작 / 1: 연속구간 / 2: 재료교체구간 / 3: 재료교체 단차 지나감
                self.check_section(data_plc=data_plc, data_vision=data_vision)

                if (self.usl_TS < 0) and (self.lsl_TS < 0) : 
                    self.usl_TS = 0; self.lsl_TS = 0; self.ref_TS = 0

                # 1. vision data for문 돌려서, 사용 가능한 데이터는 append할 것임.
                for seq in range(len(data_vision.I_cell_no)):

                    d_no = data_vision.I_cell_no[seq][0]
                    d_TP = data_vision.I_tab_pitch[seq][0]
                    d_TW = data_vision.I_tab_width[seq][0]
                    if (header.TS_VISION_DATA == 'TE'):
                        d_TS = d_TP-(d_TW + data_vision.I_tab_side[seq][0])
                    else : d_TS = data_vision.I_tab_side[seq][0]

                    # 3. 현재-이전 값 차이 계산 (치수 데이터와 Cell no)
                    self.diff_TP = d_TP - self.pre_TP
                    self.diff_TW = d_TW - self.pre_TW
                    self.diff_TS = d_TS - self.pre_TS
                    self.diff_no = d_no - self.pre_val_no

                    # 다음 데이터와의 비교를 위한 이전값 갱신
                    self.pre_TP = d_TP
                    self.pre_TW = d_TW
                    self.pre_TS = d_TS
                    self.pre_val_no = d_no

                    # Pitch보정은 Cell No 기반 계산이므로 Cell No가 초기화되면, data queue reset 필요.
                    # if (d_no < 0) or (self.diff_no < 0): self.clear_queue()

                    # 4. 현재-이전 값 차이가 0이 아니고, 특정값 이내인지 체크
                    # (USL-LSL)의미 : 연속공정의 특성 상, 이전 Cell과의 데이터가 (USL-LSL) 정도의 큰 변화를 보이기 힘듬 → 오측 판단
                    if (self.diff_no != 0) \
                        and (abs(self.diff_TP) <= (self.usl_TP-self.lsl_TP)*2) \
                        and (abs(self.diff_TW) <= (self.usl_TW-self.lsl_TW)*2) \
                        and (abs(self.diff_TS) <= (self.usl_TS-self.lsl_TS)*2) :

                        # 5. 현재 데이터가 gathering 허용 범위 내에 있는지 체크
                        if (d_TP < (self.usl_TP+self.tolerance)) and (d_TP > (self.lsl_TP-self.tolerance)) \
                            and (d_TW < (self.usl_TW+self.tolerance)) and (d_TW > (self.lsl_TW-self.tolerance)) \
                            and (d_TS < (self.usl_TS+self.tolerance)) and (d_TS > (self.lsl_TS-self.tolerance)) :  

                            # 6. 사용 가능한 데이터 수집
                            self.qCELLNO.append(d_no)
                            self.qTP.append(d_TP)
                            self.qTW.append(d_TW)
                            self.qTS.append(d_TS)

                # 수집한 데이터가 제어주기 이상 쌓이면, 자동보정 offset 계산 시작
                if (len(self.qTP) >= self.control_cycle) and (self.chk_section != 2):

                    sum_TP, sum_TW, sum_TS = 0, 0, 0

                    for n in range(self.control_cycle):
                        sum_TP += self.qTP.popleft()
                        sum_TW += self.qTW.popleft()
                        sum_TS += self.qTS.popleft()

                    mean_TP = sum_TP/self.control_cycle
                    mean_TW = sum_TW/self.control_cycle
                    mean_TS = sum_TS/self.control_cycle

                    self.offset_TP = self.check_limit((self.ref_TP - mean_TP) * self.pgain, self.limit)
                    self.offset_TW = self.check_limit((self.ref_TW - mean_TW) * self.pgain, self.limit)
                    self.offset_TS = self.check_limit((self.ref_TS - mean_TS) * self.pgain, self.limit)

                    self.control_count += 1

                    return {"TP" : round(self.offset_TP,3),
                            "TW" : round(self.offset_TW,3),
                            "TS" : round(self.offset_TS,3)}

            elif (data_plc.electrode_break_mode == 1):
                self.clear_queue()

            else:
                self.clear_queue()

            return {}

        except Exception as ex:
            message = "Control_X_Laser Error"
            utility.log_write(f"Control_X_Laser Error : {ex}")
            utility.alarm_code_refresh(msg=message, err_code=status_code.X_Axis_Auto_Logic_Alarm)

    def check_limit(self, value, limit) :
    
        if (value < -limit) : return -limit
        if (value > limit) : return limit

        return value