import header
from collections import deque
import utility
import status_code



class Control_Y:

    def __init__(self):
        self.init_update()

    def init_update(self):

        self.control_count = 0  # 자동보정 횟수 카운트
        self.result_offset = 0  # 자동보정 offset

        # ㅊㅇㅇ - laser노칭은 tab, bottom 검사하므로 변수 추가함
        self.diff_tab_top = 0       # tab top data간 차이값 (현재 - 이전)
        self.diff_tab_back = 0      # tab back data간 차이값 (현재 - 이전)
        self.diff_bottom_top = 0    # bottom top data간 차이값 (현재 - 이전)
        self.diff_bottom_back = 0   # bottom back data간 차이값 (현재 - 이전)
        self.diff_no = 0            # cell no 차이값 (현재 - 이전)

        # ㅊㅇㅇ - laser노칭은 tab, bottom 검사하므로 변수 추가함
        self.pre_val_tab_top = 0            
        self.pre_val_tab_back = 0           
        self.pre_val_bottom_top = 0
        self.pre_val_bottom_back = 0
        self.pre_val_no = 0                 # cell no data 이전값 기억변수

        # ㅊㅇㅇ - laser노칭은 tab, bottom 검사하므로 변수 추가함
        self.q_tab_top = deque(maxlen=500)
        self.q_tab_back = deque(maxlen=500)
        self.q_bottom_top = deque(maxlen=500)
        self.q_bottom_back = deque(maxlen=500)

        self.lc_start_idx = 0   # Lot Change 시작 cell index 기억 변수
    
    def clear_queue(self):
        self.q_tab_top.clear()
        self.q_tab_back.clear()
        self.q_bottom_top.clear()
        self.q_bottom_back.clear()

    # ㅊㅇㅇ : config값을 header에서 읽어옴
    def config_update(self):

        # SPEC_TCH_REF + CMD_OFFSET_Y → SPEC_TCH_TARGET

        # ㅊㅇㅇ - control_mold_epc.py 변수
        # self.target = self.ref + header.CMD_OFFSET_Y            # Target (SPEC_TCH_REF + CMD_OFFSET_Y)

        self.usl_tab = header.SPEC_TCH_USL
        self.ref_tab = header.SPEC_TCH_REF
        self.lsl_tab = header.SPEC_TCH_LSL                                        
        self.usl_bottom = header.SPEC_BCH_USL                   # ! ㅊㅇㅇ - header에 변수 추가
        self.ref_bottom = header.SPEC_BCH_REF                   # ! ㅊㅇㅇ - header에 변수 추가
        self.lsl_bottom = header.SPEC_BCH_LSL                   # ! ㅊㅇㅇ - header에 변수 추가

        self.cmdoffset = header.CMD_OFFSET_Y                                      
        
        self.target_tab = self.ref_tab + self.cmdoffset         # ! ㅊㅇㅇ - 한번 더 체크
        self.target_bottom = self.ref_bottom                    # ! ㅊㅇㅇ - 한번 더 체크

        self.pgain = header.GAIN_Y                            # 비례 제어 계수 (연속 구간)
        self.control_cycle = header.CONTROL_CYCLE_Y           # 제어 주기 (연속 구간)
        
        if self.pgain > 1.0: 
            self.pgain == 1.0                                   # 최대 100% 제한
        if self.control_cycle < 30: 
            self.control_cycle == 30                            # 최소 30Cell 이상 제하
            
        self.pgain_lc = header.GAIN_Y_LC                      # 비례 제어 계수 (Lot Change 구간)
        self.control_cycle_lc = header.CONTROL_CYCLE_Y_LC     # 제어 주기 (Lot Change 구간)
        
        if self.pgain_lc > 1.0: 
            self.pgain_lc == 1.0                                # 최대 100% 제한
        if self.control_cycle_lc < 20: 
            self.control_cycle_lc == 20                         # 최소 20Cell 이상 제하
            
        self.limit = header.OFFSET_Y_LIMIT                    # 1회 최대 보정량 (절대값)
        self.tolerance = header.GATHER_TOL_Y                  # Data Gathering Tolerance (LSL-tolerance) ~ (USL+tolerance) 범위의 데이터만 취득


        self.chk_section = 0   # 0: 시작 / 1: 연속구간 / 2: 재료교체구간 / 3: 재료교체 단차 지나감
		
        # header.DIST_AS_LPC : 테이프 붙힌 지점에서 부터 검사기까지의 거리 (19m)
        # self.lc_diff_idx: 그 거리 내에서의 Cell(탭) 갯수
        
        self.lc_diff_idx = (header.DIST_AS_LPC//header.SPEC_TP_REF)     # Lot Change 시작 ~ LPC 단차 인식 Cell 개수

        # config 변경 되었으므로, 취득한 데이터 전부 제거
        self.clear_queue()
        
        log_msg = f'Spec.(Y) : Tab - {self.usl_tab} / {self.ref_tab} / {self.lsl_tab}, \n Bottom - {self.usl_bottom} / {self.ref_bottom} / {self.lsl_bottom}, \n Auto Target : tab {self.target_tab}, bottom {self.target_bottom} (cmd offset : {self.cmdoffset} \n Para. : P Gain {self.pgain} / Cycle {self.control_cycle}tab'
        
        # CONFIG 파일이 계속 없을 경우, 로그 과출력 방지용.(1분에 한번씩만 찍도록 변경) 
        utility.log_write(log_msg, name='cl_control_Y', delay=60)

    def run(self, data_plc, data_vision):

        self.return_offset=0

        try:
            if (data_vision.notching_side == "SINGLE") : 
                self.return_offset = self.get_tab_side_Y_offset(data_plc=data_plc, data_vision=data_vision)

            elif (data_vision.notching_side == "BOTH") :
                self.return_offset = self.get_tab_bottom_side_Y_offset(data_plc=data_plc, data_vision=data_vision)

            else : 
                self.return_offset = 0

            return self.return_offset

        except Exception as ex:
            message = "Control_Y Error"
            utility.log_write(f"Control_Y Error : {ex}")
            utility.alarm_code_refresh(msg=message, err_code=status_code.Y_Axis_Auto_Logic_Alarm)

    def check_section(self, data_plc, data_vision):
                
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

    def get_tab_side_Y_offset(self, data_plc, data_vision):

        try:
            # 자동보정 로직 실행 여부 체크 (PLC 데이터 마지막 행 기준이라서 index -1로 지정)
            if (data_plc.y_button== 1) and (data_plc.electrode_break_mode== 0):

                # 연속구간/재료교체구간에 따라 파라미터(gain, cycle) 최적화
                # self.chk_section = 0   # 0: 시작 / 1: 연속구간 / 2: 재료교체구간 / 3: 재료교체 단차 지나감
                self.check_section(data_plc=data_plc, data_vision=data_vision)
                    
                # 1. vision data for문 돌려서, 사용 가능한 데이터는 append할 것임.
                for seq in range(len(data_vision.I_cell_no)):

                    # 2. 모델 구분
                    d_top = data_vision.I_top_shulder_line[seq][0]
                    d_back = data_vision.I_back_shulder_line[seq][0]
                    self.offset_direction = data_vision.offset_direction
                    
                    # 3. 현재-이전 값 차이 계산 (치수 데이터와 Cell no)
                    self.diff_top = d_top - self.pre_val_tab_top
                    self.diff_back = d_back - self.pre_val_tab_back
                    self.diff_no = data_vision.I_cell_no[seq][0] - self.pre_val_no

                    # 다음 데이터와의 비교를 위한 이전값 갱신
                    self.pre_val_tab_top = d_top
                    self.pre_val_tab_back = d_back
                    self.pre_val_no = data_vision.I_cell_no[seq][0]

                    # 4. 현재-이전 값 차이가 0이 아니고, 특정값 이내인지 체크
                    # (USL-LSL)의미 : 연속공정의 특성 상, 이전 Cell과의 데이터가 (USL-LSL) 정도의 큰 변화를 보이기 힘듬 → 오측 판단
                    if (self.diff_no != 0) and \
                        (abs(self.diff_top) > 0) and (abs(self.diff_top) < (self.usl_tab-self.lsl_tab)) and \
                        (abs(self.diff_back) > 0) and (abs(self.diff_back) < (self.usl_tab-self.lsl_tab)):

                        # 5. 현재 데이터가 gathering 허용 범위 내에 있는지 체크
                        if (d_top < (self.usl_tab+self.tolerance)) and (d_top > (self.lsl_tab-self.tolerance)) \
                            and (d_back < (self.usl_tab + self.tolerance)) and (d_back > (self.lsl_tab - self.tolerance)):

                            # 6. 사용 가능한 데이터 수집
                            self.q_tab_top.append(d_top)
                            self.q_tab_back.append(d_back)

                # 수집한 데이터가 제어주기 이상 쌓이면, 자동보정 offset 계산 시작
                if (len(self.q_tab_top) >= self.c_cycle) and (len(self.q_tab_back) >= self.c_cycle) and (self.chk_section != 2):
                    
                    sum_TCH = 0 # 변수 초기화
                    # 제어주기 만큼 queue에서 꺼낸 뒤, 1Cell 당 Top/Back 치수 데이터의 평균값 저장
                    for n in range(self.c_cycle):
                        sum_TCH += (self.q_tab_top.popleft() + self.q_tab_back.popleft())/2
                    # 자동보정 Offset = Error(SPEC REF - 데이터 평균치) * gain * 보정방향(1 or -1)

                    self.result_offset = (self.target_tab - (sum_TCH/self.c_cycle)) * self.p_gain * self.offset_direction
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
            message = "Control_Y_Tab Error"
            utility.log_write(f"Control_Y_Tab Error : {ex}")
            utility.alarm_code_refresh(msg=message, err_code=status_code.X_Axis_Auto_Logic_Alarm)    

    def get_tab_bottom_side_Y_offset(self, data_plc, data_vision):

        """
        _summary_

        PLC, Vision 데이터를 전달받아 자동보정값 계산

        Parameters
        ---
        data_plc : Notch class instance
        data_vision : Vision class instance

        Returns
        ---
        self.result_offset : float, y축 자동보정값

        """

        try:
            # 자동보정 로직 실행 여부 체크 (PLC 데이터 마지막 행 기준이라서 index -1로 지정)
            if (data_plc.y_button==1) and (data_plc.electrode_break_mode==0):

                # 연속구간/재료교체구간에 따라 파라미터(gain, cycle) 최적화
                # self.chk_section = 0   # 0: 시작 / 1: 연속구간 / 2: 재료교체구간 / 3: 재료교체 단차 지나감
                self.check_section(data_plc=data_plc, data_vision=data_vision)
                
                # 1. vision data for문 돌려서, 사용 가능한 데이터는 append할 것임
                for seq in range(len(data_vision.I_cell_no)):

                    # 2. 모델 구분
                    # ㅊㅇㅇ - laser노칭은 tab, bottom 검사하므로 변수 추가함
                    d_tab_top = data_vision.I_top_shulder_line[seq][0]
                    d_tab_back = data_vision.I_back_shulder_line[seq][0]
                    d_bottom_top = data_vision.I_bottom_front_cutting_height[seq][0]
                    d_bottom_back = data_vision.I_bottom_back_cutting_height[seq][0]

                    self.offset_direction = data_vision.offset_direction

                    # 3. 현재-이전 값 차이 계산 (치수 데이터와 Cell no)
                    # ㅊㅇㅇ - laser노칭은 tab, bottom 검사하므로 변수 추가함
                    self.diff_tab_top = d_tab_top - self.pre_val_tab_top
                    self.diff_tab_back = d_tab_back - self.pre_val_tab_back
                    self.diff_bottom_top = d_bottom_top - self.pre_val_bottom_top
                    self.diff_bottom_back = d_bottom_back - self.pre_val_bottom_back

                    self.diff_no = data_vision.I_cell_no[seq][0] - self.pre_val_no

                    # 다음 데이터와의 비교를 위한 이전값 갱신
                    self.pre_val_tab_top = d_tab_top
                    self.pre_val_tab_back = d_tab_back
                    self.pre_val_bottom_top = d_bottom_top
                    self.pre_val_bottom_back = d_bottom_back
                    self.pre_val_no = data_vision.I_cell_no[seq][0]

                    # 4. 현재-이전 값 차이가 0이 아니고, 특정값 이내인지 체크
                    # (USL-LSL)의미 : 연속공정의 특성 상, 이전 Cell과의 데이터가 (USL-LSL) 정도의 큰 변화를 보이기 힘듬 → 오측 판단
                    if (self.diff_no != 0) \
                        and (abs(self.diff_tab_top) > 0) \
                        and (abs(self.diff_tab_top) < (self.usl_tab-self.lsl_tab)) \
                        and (abs(self.diff_tab_back) > 0) \
                        and (abs(self.diff_tab_back) < (self.usl_tab-self.lsl_tab)) \
                        and (abs(self.diff_bottom_top) > 0) \
                        and (abs(self.diff_bottom_top) < (self.usl_bottom-self.lsl_bottom)) \
                        and (abs(self.diff_bottom_back) > 0) \
                        and (abs(self.diff_bottom_back) < (self.usl_bottom-self.lsl_bottom)) :

                        # 5. 현재 데이터가 gathering 허용 범위 내에 있는지 체크
                        if (d_tab_top < (self.usl_tab+self.tolerance)) and (d_tab_top > (self.lsl_tab-self.tolerance)) \
                            and (d_tab_back < (self.usl_tab + self.tolerance)) and (d_tab_back > (self.lsl_tab - self.tolerance)) \
                            and (d_bottom_top < (self.usl_bottom+self.tolerance)) and (d_bottom_top > (self.lsl_bottom-self.tolerance))\
                            and (d_bottom_back < (self.usl_bottom+self.tolerance)) and (d_bottom_back > (self.lsl_bottom-self.tolerance)):

                            # 6. 사용 가능한 데이터 수집
                            self.q_tab_top.append(d_tab_top)
                            self.q_tab_back.append(d_tab_back)
                            self.q_bottom_top.append(d_bottom_top)
                            self.q_bottom_back.append(d_bottom_back)

                # 수집한 데이터가 제어주기 이상 쌓이면, 자동보정 offset 계산 시작
                if (len(self.q_tab_top) >= self.c_cycle) and (self.chk_section != 2):

                    sum_tab_top = 0
                    sum_tab_back = 0
                    sum_bottom_top = 0
                    sum_bottom_back = 0
                    sum_tab_mean = 0
                    sum_bottom_mean = 0

                    for n in range(self.c_cycle):
                    
                        sum_tab_top += self.q_tab_top.popleft()
                        sum_tab_back += self.q_tab_back.popleft()
                        sum_bottom_top += self.q_bottom_top.popleft()
                        sum_bottom_back += self.q_bottom_back.popleft()

                    # 평균값
                    tab_top_mean = sum_tab_top/self.c_cycle
                    tab_back_mean = sum_tab_back/self.c_cycle
                    bottom_top_mean = sum_bottom_top/self.c_cycle
                    bottom_back_mean = sum_bottom_back/self.c_cycle

                    tab_mean = (tab_top_mean + tab_back_mean)/2
                    bottom_mean = (bottom_top_mean + bottom_back_mean)/2

                    # TCH_U, TCH_L값 확인
                    if (tab_top_mean >= tab_back_mean) :
                        TCH_U, TCH_L = self.usl_tab - tab_top_mean, tab_back_mean - self.lsl_tab
                    else :
                        TCH_U, TCH_L = self.usl_tab - tab_back_mean, tab_top_mean - self.lsl_tab

                    # BCH_U, BCH_L값 확인
                    if (bottom_top_mean >= bottom_back_mean) :
                        BCH_U, BCH_L = self.usl_bottom - bottom_top_mean, bottom_back_mean - self.lsl_bottom
                    else :
                        BCH_U, BCH_L = self.usl_bottom - bottom_back_mean ,bottom_top_mean - self.lsl_bottom
                    
                    # Gap A,B,C,D를 정한다
                    if (self.usl_tab-self.lsl_tab)<=(self.usl_bottom-self.lsl_bottom):
                        if (TCH_U < TCH_L):
                            Gap_A = TCH_U; Gap_B = TCH_L; Gap_C = BCH_U; Gap_D = BCH_L
                            offset_direction_2 = 1
                        else : 
                            Gap_A = TCH_L; Gap_B = TCH_U; Gap_C = BCH_L ; Gap_D = BCH_U
                            offset_direction_2 = -1
                        
                        self.target_control = self.target_tab
                        self.pv_control = tab_mean
                        offset_direction_1 = 1
                        
                    else :
                        if (BCH_U < BCH_L):
                            Gap_A = BCH_U; Gap_B = BCH_L; Gap_C = TCH_U; Gap_D = TCH_L
                            offset_direction_2 = -1
                        else :
                            Gap_A = BCH_L; Gap_B = BCH_U; Gap_C = TCH_L ; Gap_D = TCH_U
                            offset_direction_2 = 1
                        
                        self.target_control = self.target_bottom
                        self.pv_control = bottom_mean
                        offset_direction_1 = -1

                    # 제어 offset 계산1
                    if (Gap_A+Gap_B<0.2) or (Gap_A+Gap_C<0.2) or (Gap_B+Gap_D<0.2) or (Gap_C+Gap_D<0.2):

                        min_sum = min(Gap_A+Gap_B,Gap_A+Gap_C,Gap_B+Gap_D,Gap_C+Gap_D)

                        if (min_sum == Gap_A + Gap_B):
                            offset = ((Gap_A-Gap_B)/2) * self.p_gain * offset_direction_2
                        elif (min_sum == Gap_A + Gap_C):
                            offset = ((Gap_A-Gap_C)/2) * self.p_gain * offset_direction_2
                        elif (min_sum == Gap_B + Gap_D):
                            offset = ((Gap_D-Gap_B)/2) * self.p_gain * offset_direction_2
                        elif (min_sum == Gap_C+Gap_D):
                            offset = ((Gap_D-Gap_C)/2) * self.p_gain * offset_direction_2

                    else :
                    # 제어 offset 계산2

                        offset = (self.target_control - self.pv_control) * self.p_gain * offset_direction_1

                        if (Gap_C + (offset) * (offset_direction_2) < 0.1):
                            offset = (0.1-Gap_C) * self.p_gain * offset_direction_2

                        elif (Gap_D - (offset) * (offset_direction_2) < 0.1):
                            offset = (Gap_D-0.1) * self.p_gain * offset_direction_2

                    self.result_offset = offset * self.offset_direction
                    if (self.result_offset < -self.limit): self.result_offset = -self.limit
                    if (self.result_offset > self.limit): self.result_offset = self.limit
                    self.control_count += 1
                    return round(self.result_offset, 3)

            elif data_plc.electrode_break_mode == 1:
                self.clear_queue()

            else:
                self.clear_queue()

            return 0

        except Exception as ex:
            message = "Control_Y_Tab_Bottom Error"
            utility.log_write(f"Control_Y_Tab_Bottom Error : {ex}")
            utility.alarm_code_refresh(msg=message, err_code=status_code.Y_Axis_Auto_Logic_Alarm)
