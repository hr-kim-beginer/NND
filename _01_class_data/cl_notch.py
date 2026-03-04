import os 
import time
import importlib
import header
import traceback
import utility
import data_memory as dm
import status_code
import numpy as np


class Notch:
    def __init__(self, data_set):
        # R2R config 변경 여부 확인
        self.config_id = None
        self.prev_apc_use = None
        self.prev_writeplc = None
        self.prev_autostatus = None
        self.prev_electrode_break_mode = None
        self.prev_lot_change_mode = None
        self.config_value_check = None
        self.prev_model_id = None
        dm.cavity_num = None

        self.no_config = False
        self.read_new_config = False
        self.writeplc_on = False
        self.autostatus_on = False
        self.apc_use_on = False
        self.config_change_check= False
        self.model_change = False
        
        
    def update(self, data_set):
        """_summary_
        : raw data 전처리 및 변수 할당
        
            Args:
                data_set (object): raw data, column명, index가 포함된 객체
        """        
        
        try:
            self.data_ready = False
            self.data_set = data_set
            
            #^ Config ID 변경 / Config 정보 변경 여부 확인
            self.check_config_file(data_set)
            
            # 최신 데이터 조회!
            self.eqp_id = data_set.last_data([header.I_EQPID])[0]
            self.algversion = data_set.last_data([header.I_ALGVERSION])[0]
            
            self.equipment_state = data_set.last_data([header.I_EQUIPMENT_STATE])[0]
            self.m_cell_count = data_set.last_data([header.I_M_CELL_COUNT])[0]
            
            self.autostatus = data_set.last_data([header.I_AUTOSTATUS])[0]
            self.heartbeat = data_set.last_data([header.I_HEARTBEAT])[0]
            self.writeplc = data_set.last_data([header.I_WRITEPLC])[0]
            
            # Config 정보
            self.spec_tp_usl = data_set.last_data([header.I_SPEC_TP_USL])[0]
            self.spec_tp_lsl = data_set.last_data([header.I_SPEC_TP_LSL])[0]
            
            self.spec_tn_usl = self.check_plc_column(header.I_SPEC_TN_USL)
            self.spec_tn_lsl = self.check_plc_column(header.I_SPEC_TN_LSL)
            
            self.spec_tch_usl = self.check_plc_column(header.I_SPEC_TCH_USL)
            self.spec_tch_lsl = self.check_plc_column(header.I_SPEC_TCH_LSL)

            self.spec_bch_usl = self.check_plc_column(header.I_SPEC_BCH_USL)
            self.spec_bch_lsl = self.check_plc_column(header.I_SPEC_BCH_LSL)

            self.spec_tw_usl = data_set.last_data([header.I_SPEC_TW_USL])[0]
            self.spec_tw_lsl = data_set.last_data([header.I_SPEC_TW_LSL])[0]

            self.spec_ts_usl = self.check_plc_column(header.I_SPEC_TS_USL)
            self.spec_ts_lsl = self.check_plc_column(header.I_SPEC_TS_LSL)
            
            # self.spec_tp_ref = self.check_plc_column(header.I_SPEC_TP_REF)
            # self.spec_tch_ref = self.check_plc_column(header.I_SPEC_TCH_REF)
            # self.spec_bch_ref = self.check_plc_column(header.I_SPEC_BCH_REF)
            # self.spec_tw_ref = self.check_plc_column(header.I_SPEC_TW_REF)
            # self.spec_ts_ref = self.check_plc_column(header.I_SPEC_TS_REF)

            # self.x_gain = self.check_plc_column(header.I_X_GAIN)
            # self.y_gain = self.check_plc_column(header.I_Y_GAIN)

            # self.x_ctrl_cycle_cell = self.check_plc_column(header.I_X_CTRL_CYCLE_CELL)
            # self.y_ctrl_cycle_cell = self.check_plc_column(header.I_Y_CTRL_CYCLE_CELL)

            # self.y_target = self.check_plc_column(header.I_Y_TARGET)
            # self.x_target = self.check_plc_column(header.I_X_TARGET)

            # self.y_target_offset = self.check_plc_column(header.I_Y_TARGET_OFFSET)
            # self.x_target_offset = self.check_plc_column(header.I_X_TARGET_OFFSET)
           
            # list_of_pairs = \
            #     [
            #         ['SPEC_TP_REF', self.spec_tp_ref, (header.SPEC_TP_REF*header.HUNDRED)],
            #         ['SPEC_TCH_REF', self.spec_tch_ref, (header.SPEC_TCH_REF*header.HUNDRED)],
            #         ['SPEC_BCH_REF', self.spec_bch_ref, (header.SPEC_BCH_REF*header.HUNDRED)],
            #         ['SPEC_TW_REF', self.spec_tw_ref, (header.SPEC_TW_REF*header.HUNDRED)],
            #         ['SPEC_TS_REF', self.spec_ts_ref, (header.SPEC_TS_REF*header.HUNDRED)],
            #         ['GAIN_X', self.x_gain, (header.GAIN_X*header.HUNDRED)],
            #         ['GAIN_Y', self.y_gain, (header.GAIN_Y*header.HUNDRED)],
            #         ['CONTROL_CYCLE_X', self.x_ctrl_cycle_cell, header.CONTROL_CYCLE_X],
            #         ['CONTROL_CYCLE_Y', self.y_ctrl_cycle_cell, header.CONTROL_CYCLE_Y],
            #         ['Y_TARGET', self.y_target, (header.SPEC_TCH_REF + header.CMD_OFFSET_Y)*header.HUNDRED],
            #         ['X_TARGET', self.x_target, (header.SPEC_TP_REF*header.HUNDRED)],
            #         ['Y_TARGET_OFFSET', self.y_target_offset, (header.CMD_OFFSET_Y*header.HUNDRED)],
            #         ['X_TARGET_OFFSET', self.x_target_offset, 0] #! 향후, Config 추가 예정
            #     ]
            
            self.last_data_time = data_set.last_data([header.I_TIME])[0]
            self.model_id = data_set.last_data([header.I_MODEL_ID])[0]
            # self.autoon_button = data_set.last_data([header.I_AUTOON_BUTTON])[0]
            
            self.electrode_break_mode = data_set.last_data([header.I_ELECTRODE_BREAK_MODE])[0]
            self.lot_change_mode = data_set.last_data([header.I_LOT_CHANGE_MODE])[0]
            
            self.feeding_speed_servo = data_set.last_data([header.I_FEEDING_SPEED_SERVO])[0]

            self.x_button =  data_set.last_data([header.I_X_BUTTON])[0]
            self.y_button =  data_set.last_data([header.I_Y_BUTTON])[0]
                                    
            self.x_tp_pv_val = data_set.last_data([header.I_X_TP_PV_VAL])[0]
            self.x_tw_pv_val = self.check_plc_column(header.I_X_TW_PV_VAL)
            self.x_ts_pv_val = self.check_plc_column(header.I_X_TS_PV_VAL)

            self.y_pv_val = data_set.last_data([header.I_Y_PV_VAL])[0]
            
            dm.cavity_num = self.check_plc_column(header.I_CAVITY_NUM, replace=0)
            
            if isinstance(self.model_id, str):
                self.model_id.strip()     

            #^ Write Config to Result File
            # 1) Write PLC 정보가 OFF→ON될때, 
            self.check_write_plc_change()
            # 2) Read한 값과 Config값이 다를 경우, 
            # self.config_change_check = self.check_read_config_change(list_of_pairs)
                        
            if dm.shoulder_line:
                #^ 모델 변경 확인
                self.model_chage_check()
                #^ PLC 내 모델 SPEC정보와 Config 내 값 확인(USL, LSL)
                self.check_config_value()
            else:
                self.config_value_check = None
            
            self.data_ready = True
            
        except Exception as e:
            utility.log_write_by_level("Notch PLC data update 에러...{}".format(e), level='critical', delay=10) 
            utility.log_write(traceback.format_exc(), name='cl_notch', delay=60)


    def read_config(self):
        try:
            config_path = os.path.join(os.path.normpath(header.CSV_FILE_PATH_CONFIG), self.config_id)
            dm.model_config_path = config_path

            if os.path.isfile(dm.model_config_path):
                importlib.reload(header)
                dm.updated_eqp_config_time = os.path.getmtime(dm.eqp_config_path)
                dm.updated_model_config_time = os.path.getmtime(dm.model_config_path)
                
                print("\033[1m\033[93m" + f"\nConfig 파일이 {os.path.basename(dm.model_config_path)}로 변경되었습니다!!\n" + "\033[0m")
                header.all_print(header.config)
                self.read_new_config = False
            else:
                dm.updated_model_config_time = None
                message = f"Not_Found_Config_File_Alarm, {self.config_id}"
                utility.write_log_alarm(message, err_code=status_code.Not_Found_Config_Alarm)
                time.sleep(header.WAIT_TIME_SEC) # 1초
                
        except Exception as ex:
            dm.updated_model_config_time = None
            utility.log_write('Config read 에러..... ' + utility.error_msg(ex))
        

    def break_mode_change_check(self):
        if self.electrode_break_mode != self.prev_electrode_break_mode:
            if self.prev_electrode_break_mode == None:
                pass
            else:
                if self.electrode_break_mode:
                    utility.log_write("파단모드 진입.")
                else:
                    utility.log_write("파단모드 종료.")
            self.prev_electrode_break_mode = self.electrode_break_mode
            
    def lot_chage_check(self):
        if (self.lot_change_mode != self.prev_lot_change_mode):
            if self.prev_lot_change_mode == None:
                pass
            else:
                if self.lot_change_mode:
                    utility.log_write("재료교체 모드 진입.")
                else:
                    utility.log_write("재료교체 모드 종료.")
            self.prev_lot_change_mode = self.lot_change_mode


    def model_chage_check(self):

        if (self.prev_model_id == None) and (self.model_id != self.prev_model_id):
            self.model_change = True
            self.prev_model_id = self.model_id
        elif (self.prev_model_id != None) and (self.model_id != self.prev_model_id):
            utility.log_write(f"모델이 {self.prev_model_id} -> {self.model_id}로 변경되었습니다.")
            self.model_change = True
            self.prev_model_id = self.model_id
        # else:
        #     self.model_change = False    
            

    @staticmethod        
    def are_different(value1, value2):
        return round(value1, 2) != round(value2, 2)

    def check_plc_column(self, col_name, replace=-1):
        if col_name not in self.data_set.column_name:
            return replace
        else : return self.data_set.last_data([col_name])[0]

    def check_read_config_change(self, list_of_pairs):

        list_of_exception = ['SPEC_BCH_REF', 'SPEC_TW_REF', 'SPEC_TS_REF']

        for pair in list_of_pairs:

            if self.are_different(pair[1], pair[2]):
            # ㅊㅇㅇ - pair[1] : PLC, pair[2] : config

                if pair[1] <= 0 : continue

                if pair[0] in list_of_exception :
                    if pair[2] <= 0 : continue

                utility.log_write(f"Config File 내, {pair[0]} 값이 읽은 정보와 다릅니다.({pair[1]}, {pair[2]})", name='cl_notch', delay=60)
                
                return True

        return False
    
    def write_sv_val_zero(self):
        pass

    def check_write_plc_change(self):
        # OFF
        # 1) Write PLC OFF, 2) APC_USE OFF Alarm 등록
        if self.writeplc == 0:
            message = f"WRITEPLC_Off_Alarm Occurred!!"
            utility.alarm_code_refresh(msg=message, err_code=status_code.WRITEPLC_Off_Alarm)
            utility.log_write(message, name='cl_notch', delay=60)

        # OFF -> ON        
        # 1) APC Write PLC 기능이 OFF→ON 될 때, Config 정보 업데이트 
        if ((self.prev_writeplc== 0) or (self.prev_writeplc==None)) and (self.writeplc==1):
            self.writeplc_on = True

        # 이전 값을 현재 값으로 업데이트
        self.prev_writeplc = self.writeplc

        # 2) APC Write PLC 기능이 None→ON 될 때

    def check_auto_status_change(self):                
        # 1) Algorithm Status 상태가 OFF→ON 될 때, Config 정보 업데이트 
        if ((self.prev_autostatus== 0) or (self.prev_autostatus==None)) and (self.autostatus==1):
            self.autostatus_on = True
        # 이전 값을 현재 값으로 업데이트
        self.prev_autostatus = self.autostatus

    def check_apc_use_change(self):
        # 1) Write PLC OFF, 2) APC_USE OFF Alarm 등록
        if self.apc_use == 0:
            message = f"APC_USE_Off_Alarm Occurred!!"
            utility.alarm_code_refresh(msg=message, err_code=status_code.APC_USE_Off_Alarm)
            utility.log_write(message, name='cl_notch', delay=60)
       
        # 1) APC Write PLC 기능이 OFF→ON 될 때, Config 정보 업데이트 
        if (self.prev_apc_use== 0) and (self.apc_use==1):
            self.apc_use_on = True
        # 이전 값을 현재 값으로 업데이트
        self.prev_apc_use = self.apc_use
        
        
    # ! ㅊㅇㅇ - 레이저 노칭 Spec 추가 
    def check_config_value(self):
        self.config_value_check = None

        if (self.model_change):

            # TN
            if self.spec_tn_lsl == 0 and self.spec_tn_usl == 0 :
                self.spec_tn_lsl = -1
                self.spec_tn_usl = -1

            # TCH
            if self.spec_tch_lsl == 0 and self.spec_tch_usl == 0 :
                self.spec_tch_lsl = -1
                self.spec_tch_usl = -1

            # TN, TCH
            if header.SPEC_TCH_LSL == 0 and header.SPEC_TCH_USL == 0 :
                header.SPEC_TCH_LSL = -1
                header.SPEC_TCH_USL = -1

            # BCH
            if self.spec_bch_lsl == 0 and self.spec_bch_usl == 0 :
                self.spec_bch_lsl = -1
                self.spec_bch_usl = -1

            if header.SPEC_BCH_LSL == 0 and header.SPEC_BCH_USL == 0 :
                header.SPEC_BCH_LSL = -1
                header.SPEC_BCH_USL = -1

            # TS
            if self.spec_ts_lsl == 0 and self.spec_ts_usl == 0 :
                self.spec_ts_lsl = -1
                self.spec_ts_usl = -1

            if header.SPEC_TS_LSL == 0 and header.SPEC_TS_USL == 0 :
                header.SPEC_TS_LSL = -1
                header.SPEC_TS_USL = -1                

            # 어깨선 항목 검사 데이터 매핑
            if dm.shoulder_line == "TCH":
                shoulder_usl = self.spec_tch_usl
                shoulder_lsl = self.spec_tch_lsl
            elif dm.shoulder_line == "TN":
                shoulder_usl = self.spec_tn_usl
                shoulder_lsl = self.spec_tn_lsl

            # 모델 SPEC 값 일치 여부 확인     
            
            if header.MACHINE_TYPE == 'MOLD' :

                shoulder_usl = self.spec_tch_usl
                shoulder_lsl = self.spec_tch_lsl

                if (round(self.spec_tp_usl,2) == round(header.SPEC_TP_USL,2)) and (round(self.spec_tp_lsl,2) == round(header.SPEC_TP_LSL,2)) \
                and (round(shoulder_usl,2) == round(header.SPEC_TCH_USL,2)) and (round(shoulder_lsl,2) == round(header.SPEC_TCH_LSL,2)) :

                    self.config_value_check = False
                    self.model_change = False

                else :

                    # Shoulder Line SPEC 정보 확인
                    if round(shoulder_usl,2) != round(header.SPEC_TCH_USL,2):
                        message = f"[{dm.shoulder_line}_USL] PLC 내 모델 SPEC 정보와 Config 파일 내 정보가 다릅니다. ({shoulder_usl}, {header.SPEC_TCH_USL})"
                    elif round(shoulder_lsl,2) != round(header.SPEC_TCH_LSL,2):
                        message = f"[{dm.shoulder_line}_LSL] PLC 내 모델 SPEC 정보와 Config 파일 내 정보가 다릅니다. ({shoulder_lsl}, {header.SPEC_TCH_LSL})"               
                        
                    # TAB PITCH SPEC 정보 확인
                    if round(self.spec_tp_usl,2) != round(header.SPEC_TP_USL,2):
                        message = f"[TP_USL] PLC 내 모델 SPEC 정보와 Config 파일 내 정보가 다릅니다. ({self.spec_tp_usl}, {header.SPEC_TP_USL})"
                    elif round(self.spec_tp_lsl,2) != round(header.SPEC_TP_LSL,2):
                        message = f"[TP_LSL] PLC 내 모델 SPEC 정보와 Config 파일 내 정보가 다릅니다. ({self.spec_tp_lsl}, {header.SPEC_TP_LSL})"
                
                    # self.model_change = True
                    self.config_value_check = True
                    utility.log_write(message, name='cl_notch', delay=60)    

            elif header.MACHINE_TYPE == 'LASER' :

                # ESMI 검사기에서 TS spec이 아닌 TE spec을 보내주는 경우가 있어 예외처리 추가
                con_ts = (round(self.spec_ts_usl,2) == round(header.SPEC_TS_USL,2)) and (round(self.spec_ts_lsl,2) == round(header.SPEC_TS_LSL,2))

                if not con_ts :
                    # APC config에 입력된 TS spec을 TE spec으로 변환하여 PLC spec과 비교
                    apc_spec_te_usl = round(header.SPEC_TP_REF,2)-round(header.SPEC_TW_REF,2)-round(header.SPEC_TS_LSL,2)
                    apc_spec_te_lsl = round(header.SPEC_TP_REF,2)-round(header.SPEC_TW_REF,2)-round(header.SPEC_TS_USL,2)

                    con_ts = (round(self.spec_ts_usl,2) == round(apc_spec_te_usl,2)) and (round(self.spec_ts_lsl,2) == round(apc_spec_te_lsl,2))

                if (round(self.spec_tp_usl,2) == round(header.SPEC_TP_USL,2)) and (round(self.spec_tp_lsl,2) == round(header.SPEC_TP_LSL,2)) \
                and (round(self.spec_tw_usl,2) == round(header.SPEC_TW_USL,2)) and (round(self.spec_tw_lsl,2) == round(header.SPEC_TW_LSL,2)) \
                and con_ts \
                and (round(shoulder_usl,2) == round(header.SPEC_TCH_USL,2)) and (round(shoulder_lsl,2) == round(header.SPEC_TCH_LSL,2)) \
                and (round(self.spec_bch_usl,2) == round(header.SPEC_BCH_USL,2)) and (round(self.spec_bch_lsl,2) == round(header.SPEC_BCH_LSL,2)):
            
                    self.config_value_check = False
                    self.model_change = False

                else :

                    # Shoulder Line SPEC 정보 확인
                    if round(shoulder_usl,2) != round(header.SPEC_TCH_USL,2):
                        message = f"[{dm.shoulder_line}_USL] PLC 내 모델 SPEC 정보와 Config 파일 내 정보가 다릅니다. ({shoulder_usl}, {header.SPEC_TCH_USL})"
                    elif round(shoulder_lsl,2) != round(header.SPEC_TCH_LSL,2):
                        message = f"[{dm.shoulder_line}_LSL] PLC 내 모델 SPEC 정보와 Config 파일 내 정보가 다릅니다. ({shoulder_lsl}, {header.SPEC_TCH_LSL})"

                    # BCH 정보 확인
                    if round(self.spec_bch_usl,2) != round(header.SPEC_BCH_USL,2):
                        message = f"[BCH_USL] PLC 내 모델 SPEC 정보와 Config 파일 내 정보가 다릅니다. ({self.spec_bch_usl}, {header.SPEC_BCH_USL})"
                    elif round(self.spec_bch_lsl,2) != round(header.SPEC_BCH_LSL,2):
                        message = f"[BCH_LSL] PLC 내 모델 SPEC 정보와 Config 파일 내 정보가 다릅니다. ({self.spec_bch_lsl}, {header.SPEC_BCH_LSL})"                
                        
                    # TAB PITCH SPEC 정보 확인
                    if round(self.spec_tp_usl,2) != round(header.SPEC_TP_USL,2):
                        message = f"[TP_USL] PLC 내 모델 SPEC 정보와 Config 파일 내 정보가 다릅니다. ({self.spec_tp_usl}, {header.SPEC_TP_USL})"
                    elif round(self.spec_tp_lsl,2) != round(header.SPEC_TP_LSL,2):
                        message = f"[TP_LSL] PLC 내 모델 SPEC 정보와 Config 파일 내 정보가 다릅니다. ({self.spec_tp_lsl}, {header.SPEC_TP_LSL})"

                    # TAB WIDTH SPEC 정보 확인
                    if round(self.spec_tw_usl,2) != round(header.SPEC_TW_USL,2):
                        message = f"[TW_USL] PLC 내 모델 SPEC 정보와 Config 파일 내 정보가 다릅니다. ({self.spec_tw_usl}, {header.SPEC_TW_USL})"
                    elif round(self.spec_tw_lsl,2) != round(header.SPEC_TW_LSL,2):
                        message = f"[TW_LSL] PLC 내 모델 SPEC 정보와 Config 파일 내 정보가 다릅니다. ({self.spec_tw_lsl}, {header.SPEC_TW_LSL})"

                    # TAB SIDE SPEC 정보 확인
                    if round(self.spec_ts_usl,2) != round(header.SPEC_TS_USL,2):
                        message = f"[TS_USL] PLC 내 모델 SPEC 정보와 Config 파일 내 정보가 다릅니다. ({self.spec_ts_usl}, {header.SPEC_TS_USL})"
                    elif round(self.spec_ts_lsl,2) != round(header.SPEC_TS_LSL,2):
                        message = f"[TS_LSL] PLC 내 모델 SPEC 정보와 Config 파일 내 정보가 다릅니다. ({self.spec_ts_lsl}, {header.SPEC_TS_LSL})"
                
                    # self.model_change = True
                    self.config_value_check = True
                    utility.log_write(message, name='cl_notch', delay=60)           
        
    def check_config_file(self, data_set):
        # R2R Config 파일 변경
        try:
            config_id = data_set.last_data([header.I_CONFIGID])[0] # to be fixed (header에 config_id varname 추가)
            cur_eqp_config_time = os.path.getmtime(dm.eqp_config_path)
            cur_model_config_time = os.path.getmtime(dm.model_config_path)
            
            # Config_id = 'NOT_FOUND' => Not_Found_Config_Alarm 발생
            self.no_config = 'NOT_FOUND' in config_id
            
            #^ 설비 Config 변경 확인
            if (dm.updated_eqp_config_time is not None and dm.updated_eqp_config_time != cur_eqp_config_time):
                self.read_new_config = True
                str_config_time = time.ctime(cur_eqp_config_time)
                utility.write_log_alarm(message='Equipment Config Info Changed, ' + str_config_time + '  ' + config_id, err_code=status_code.Config_Changed_Alarm)
                
            #^ 모델 Config 변경 확인
            if self.no_config:
                self.config_id = config_id
                dm.updated_model_config_time = None
                message = "CONFIG ID IS NOT FOUNDED"
                utility.alarm_code_refresh(msg=message, err_code=status_code.Not_Found_Config_Alarm)

            #! Config ID가 변경되거나, Config 파일이 수정될 경우 => Flag(read_new_config) 정보 업데이트 
            elif (self.config_id != config_id) or (dm.updated_model_config_time is not None and dm.updated_model_config_time != cur_model_config_time):
                self.config_id = config_id
                self.read_new_config = True
                str_config_time = time.ctime(cur_model_config_time)
                utility.write_log_alarm(message='Model Config Info Changed, ' + str_config_time + '  ' + config_id, err_code=status_code.Config_Changed_Alarm)
            
        except FileNotFoundError:
            dm.updated_model_config_time = None
            self.read_new_config = True
            message = f"Not_Found_Config_File_Alarm, {self.config_id}"
            utility.write_log_alarm(message, err_code=status_code.Not_Found_Config_Alarm)
            time.sleep(header.WAIT_TIME_SEC) 
            
        except Exception as e:
                utility.log_write(traceback.format_exc(), name='cl_notch', delay=60)
        