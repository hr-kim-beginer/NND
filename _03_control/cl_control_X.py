import math
import numpy as np
import header
import data_memory as dm
from collections import deque
import utility
import status_code
from _02_class_function import cl_timer
from abc import ABC, abstractmethod

class Control_X(ABC):

    def __init__(self):
        self.init_update()
        self.log_count = 0
        self.tm_log = cl_timer.Ctimer()

    def init_update(self):
        self.control_count = 0  # 자동보정 횟수 카운트
        self.result_offsets = []

        self.diff_TP = 0    # tab pitch data 간 차이값 (현재 - 이전)
        self.diff_TW = 0
        self.diff_TS = 0
        self.diff_no = 0    # cell no 차이값 (현재 - 이전)

        self.qCELLNO = deque(maxlen=500)      
        self.qTP = deque(maxlen=500)       
        self.qTW = deque(maxlen=500)
        self.qTS = deque(maxlen=500)

        self.lc_start_idx = 0  # Lot Change 시작 cell index 기억 변수

    def clear_queue(self):
        self.qCELLNO.clear()
        self.qTP.clear()
        self.qTW.clear()
        self.qTS.clear()

    def config_update(self):
        
        # if not dm.cavity_num:
        #     self.clear_queue()
        #     return
        
        self.usl_TP = header.SPEC_TP_USL
        self.ref_TP = header.SPEC_TP_REF
        self.lsl_TP = header.SPEC_TP_LSL                                  

        # ㅊㅇㅇ - 변수 추가
        self.usl_TW = header.SPEC_TW_USL
        self.ref_TW = header.SPEC_TW_REF
        self.lsl_TW = header.SPEC_TW_LSL

        self.usl_TS = header.SPEC_TS_USL
        self.ref_TS = header.SPEC_TS_REF
        self.lsl_TS = header.SPEC_TS_LSL

        self.cavity_num = int(dm.cavity_num)   
        self.pvar_criteria = header.PVAR_CRITERIA

        self.pgain = header.GAIN_X                                                             # 비례 제어 계수 (연속 구간)
        # self.control_cycle = (header.CONTROL_CYCLE_X // self.cavity_num) * self.cavity_num     # 제어 주기 (연속 구간)
        self.control_cycle = header.CONTROL_CYCLE_X

        if self.pgain > 1.0: 
            self.pgain = 1.0                                                # 최대 100% 제한
        
        # 이거 mold랑 laser랑 다름
        if self.control_cycle < (self.cavity_num*25): 
            self.control_cycle = self.cavity_num*25                         # cavity당 최소 25 Cell이 있어야 분산 계산 가능
        
        self.limit = header.OFFSET_X_LIMIT                                 # 1회 최대 보정량 (절대값)
        self.tolerance = header.GATHER_TOL_X                               # Data Gathering Tolerance (LSL-tolerance) ~ (USL+tolerance) 범위의 데이터만 취득

        self.chk_section = 0                                                # 0: 시작 / 1: 연속구간 / 2: 재료교체구간 / 3: 재료교체 단차 지나감
        self.lc_diff_idx = (header.DIST_AS_LPC//header.SPEC_TP_REF)         # Lot Change 시작 ~ LPC 단차 인식 Cell 개수

        self.pre_TP = self.ref_TP           # tab pitch data 이전값 기억변수
        self.pre_TW = self.ref_TW           
        self.pre_TS = self.ref_TS
        self.pre_val_no = 0                 # cell no data 이전값 기억변수
        
        # # config 변경 되었으므로, 취득한 데이터 전부 제거
        self.clear_queue()
        log_msg =   f'Spec.(X) : TP - {self.usl_TP} / {self.ref_TP} / {self.lsl_TP}, \n TW - {self.usl_TW} / {self.ref_TW} / {self.lsl_TW}, \n TS - {self.usl_TS} / {self.ref_TS} / {self.lsl_TS}, \n Para. : P Gain {self.pgain} / Cycle {self.control_cycle}tab'
                    
        # CONFIG 파일이 계속 없을 경우, 로그 과출력 방지용.(1분에 한번씩만 찍도록 변경) 
        utility.log_write(log_msg, name='cl_control_X', delay=60)
            
    def check_section(self, data_plc, data_vision):
        
        if (data_plc.lot_change_mode == 1) and (self.chk_section < 2):
            utility.log_write("X축 재료교체구간 진입")
            self.lc_start_idx = data_vision.cell_no
            self.chk_section = 2
            utility.log_write(f"(UW A/S - Vision)구간 내 접합Tape 존재 -> X축 보정값 계산 중지")

        if (data_plc.lot_change_mode == 1) and (self.chk_section == 2):
            diff_lc_cell = data_vision.cell_no - self.lc_start_idx

            if (diff_lc_cell > self.lc_diff_idx) or (diff_lc_cell < 0):
                utility.log_write("접합Tape Vision 통과 -> Queue Reset, X축 보정 재시작")
                self.chk_section = 3
                self.clear_queue()

        if (data_plc.lot_change_mode == 0) and (self.chk_section != 1):
            utility.log_write("X축 연속구간 진입")
            utility.log_write(f"P_GAIN: {self.pgain}, C_CYCLE: {self.control_cycle}")
            self.chk_section = 1

    @abstractmethod
    def run(self):
        pass