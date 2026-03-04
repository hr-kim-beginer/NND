import header
import utility
import status_code
from collections import deque

class Control_Mold_EPC:
    def __init__(self):
        self.init_update()

    def init_update(self):
        self.control_count = 0  # 자동보정 횟수 카운트
        self.result_offset = 0  # 자동보정 offset

        self.diff_top = 0       # top data 간 차이값 (현재 - 이전)
        self.diff_back = 0      # back data 간 차이값 (현재 - 이전)
        self.diff_no = 0        # cell no 차이값 (현재 - 이전)

        self.pre_val_top = 0    # top data 이전값 기억변수
        self.pre_val_back = 0   # back data 이전값 기억변수
        self.pre_val_no = 0     # cell no data 이전값 기억변수

        self.qTCH_top = deque(maxlen=500) # top data 수집용
        self.qTCH_back = deque(maxlen=500)# back data 수집용

        self.lc_start_idx = 0   # Lot Change 시작 cell index 기억 변수
    
    def clear_queue(self):
        self.qTCH_top.clear()
        self.qTCH_back.clear()

    def config_update(self):
        # SPEC_TCH_REF + CMD_OFFSET_Y → SPEC_TCH_TARGET

        self.usl = header.SPEC_TCH_USL                          # USL
        self.ref = header.SPEC_TCH_REF                          # REF
        self.lsl = header.SPEC_TCH_LSL                          # LSL
        self.cmdoffset = header.CMD_OFFSET_Y                    # REF기준 사용자 추가 입력 offset
        self.target = self.ref + header.CMD_OFFSET_Y            # Target (SPEC_TCH_REF + CMD_OFFSET_Y)

        self.pgain = header.GAIN_TCH                            # 비례 제어 계수 (연속 구간)
        self.control_cycle = header.CONTROL_CYCLE_TCH           # 제어 주기 (연속 구간)
        
        
        if self.pgain > 1.0: 
            self.pgain = 1.0                                   # 최대 100% 제한
        if self.control_cycle < 30: 
            self.control_cycle = 30                            # 최소 30Cell 이상 제하
            
        self.pgain_lc = header.GAIN_TCH_LC                      # 비례 제어 계수 (Lot Change 구간)
        self.control_cycle_lc = header.CONTROL_CYCLE_TCH_LC     # 제어 주기 (Lot Change 구간)
        
        if self.pgain_lc > 1.0: 
            self.pgain_lc = 1.0                                # 최대 100% 제한
        if self.control_cycle_lc < 20: 
            self.control_cycle_lc = 20                         # 최소 20Cell 이상 제하
            
        self.limit = header.OFFSET_TCH_LIMIT                    # 1회 최대 보정량 (절대값)
        self.tolerance = header.GATHER_TOL_EPC                  # Data Gathering Tolerance (LSL-tolerance) ~ (USL+tolerance) 범위의 데이터만 취득


        self.chk_section = 0   # 0: 시작 / 1: 연속구간 / 2: 재료교체구간 / 3: 재료교체 단차 지나감
		
        # header.DIST_AS_LPC : 테이프 붙힌 지점에서 부터 검사기까지의 거리 (19m)
        # self.lc_diff_idx: 그 거리 내에서의 Cell(탭) 갯수
        
        self.lc_diff_idx = (header.DIST_AS_LPC//header.SPEC_TP_REF)     # Lot Change 시작 ~ LPC 단차 인식 Cell 개수

        # config 변경 되었으므로, 취득한 데이터 전부 제거
        self.clear_queue()
        
        log_msg = f'Spec.(Shoulder Line) : {self.usl} / {self.ref} / {self.lsl} \
                    Auto Target : {self.target} (cmd offset : {self.cmdoffset} \
                    Para. : P Gain {self.pgain} / Cycle {self.control_cycle}tab'
        
        # CONFIG 파일이 계속 없을 경우, 로그 과출력 방지용.(1분에 한번씩만 찍도록 변경) 
        utility.log_write(log_msg, delay=120)


    def run(self, data_plc, data_vision):

        try:
            # 자동보정 로직 실행 여부 체크 (PLC 데이터 마지막 행 기준이라서 index -1로 지정)
            if (data_plc.y_button== 1) and (data_plc.electrode_break_mode== 0):

                # 연속구간/재료교체구간에 따라 파라미터(gain, cycle) 최적화
                
                if (data_plc.lot_change_mode == 1) and (self.chk_section < 2):
                    utility.log_write("Y축 재료교체구간 진입")
                    self.lc_start_idx = data_vision.cell_no
                    self.chk_section = 2
                    self.p_gain = self.pgain
                    self.c_cycle = self.control_cycle
                    utility.log_write(f"(UW A/S - Vision)구간 내 접합Tape 존재 -> Y축 보정값 계산 중지")
                    
                if (data_plc.lot_change_mode == 1) and (self.chk_section == 2):
                    diff_lc_cell = data_vision.cell_no - self.lc_start_idx

                    if (diff_lc_cell > self.lc_diff_idx) or (diff_lc_cell < 0):
                        utility.log_write("접합Tape Vision 통과 -> Y축 재료교체 파라미터 적용")
                        self.chk_section = 3
                        self.p_gain = self.pgain_lc
                        self.c_cycle = self.control_cycle_lc
                        utility.log_write(f"P_GAIN: {self.p_gain}, C_CYCLE: {self.c_cycle}")
                        self.clear_queue()
                        
                if (data_plc.lot_change_mode == 0) and (self.chk_section != 1):
                    utility.log_write("Y축 연속구간 진입")
                    self.p_gain = self.pgain
                    self.c_cycle = self.control_cycle
                    self.chk_section = 1
                    utility.log_write(f"P_GAIN: {self.p_gain}, C_CYCLE: {self.c_cycle}")
                    
                # 1. vision data for문 돌려서, 사용 가능한 데이터는 append할 것임.
                for seq in range(len(data_vision.I_cell_no)):

                    # 2. 모델 구분
                    d_top = data_vision.I_top_shulder_line[seq][0]
                    d_back = data_vision.I_back_shulder_line[seq][0]
                    self.offset_direction = data_vision.offset_direction
                    

                    # 3. 현재-이전 값 차이 계산 (치수 데이터와 Cell no)
                    self.diff_top = d_top - self.pre_val_top
                    self.diff_back = d_back - self.pre_val_back
                    self.diff_no = data_vision.I_cell_no[seq][0] - self.pre_val_no

                    # 다음 데이터와의 비교를 위한 이전값 갱신
                    self.pre_val_top = d_top
                    self.pre_val_back = d_back
                    self.pre_val_no = data_vision.I_cell_no[seq][0]

                    # 4. 현재-이전 값 차이가 0이 아니고, 특정값 이내인지 체크
                    # (USL-LSL)의미 : 연속공정의 특성 상, 이전 Cell과의 데이터가 (USL-LSL) 정도의 큰 변화를 보이기 힘듬 → 오측 판단
                    if (self.diff_no != 0) and (abs(self.diff_top) > 0) and (abs(self.diff_top) < (self.usl-self.lsl)) and (abs(self.diff_back) > 0) and (abs(self.diff_back) < (self.usl-self.lsl)):


                        # 5. 현재 데이터가 gathering 허용 범위 내에 있는지 체크
                        if (d_top < (self.usl+self.tolerance)) and (d_top > (self.lsl-self.tolerance)) \
                            and (d_back < (self.usl + self.tolerance)) and (d_back > (self.lsl - self.tolerance)):

                            # 6. 사용 가능한 데이터 수집
                            self.qTCH_top.append(d_top)
                            self.qTCH_back.append(d_back)


                # 수집한 데이터가 제어주기 이상 쌓이면, 자동보정 offset 계산 시작
                if (len(self.qTCH_top) >= self.c_cycle) and (len(self.qTCH_back) >= self.c_cycle) and (self.chk_section != 2):
                    
                    sum_TCH = 0 # 변수 초기화
                    # 제어주기 만큼 queue에서 꺼낸 뒤, 1Cell 당 Top/Back 치수 데이터의 평균값 저장
                    for n in range(self.c_cycle):
                        sum_TCH += (self.qTCH_top.popleft() + self.qTCH_back.popleft())/2
                    # 자동보정 Offset = Error(SPEC REF - 데이터 평균치) * gain * 보정방향(1 or -1)

                    self.result_offset = (self.target - (sum_TCH/self.c_cycle)) * self.p_gain * self.offset_direction
                    # 1회 보정량 상/하한치 조정
                    if (self.result_offset < -self.limit): self.result_offset = -self.limit
                    if (self.result_offset > self.limit): self.result_offset = self.limit

                    self.control_count += 1  # 자동보정 카운트True, reverse=

                    return round(self.result_offset, 3)


            elif data_plc.electrode_break_mode == 1:
                self.clear_queue()

            else:
                self.clear_queue()

            return 0

        except Exception as ex:
            message = "Control_Mold_EPC Error"
            utility.log_write(f"Control_Mold_EPC Error : {ex}")
            utility.alarm_code_refresh(msg=message, err_code=status_code.X_Axis_Auto_Logic_Alarm)
            