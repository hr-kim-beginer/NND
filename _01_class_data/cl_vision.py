import header
import traceback
import utility
import data_memory as dm
import numpy as np

class Vision:
    def __init__(self, data_set):
        self.prefix_name = data_set.prefix_name   # Vision
        self.prev_lot_id = None


    def update(self, data_set):
        try:

            self.data_ready = False
            self.data_set = data_set
            
            # 최신 데이터 조회!
            self.judge = data_set.last_data([header.I_JUDGE])[0]
            self.cell_no = data_set.last_data([header.I_CELL_NO])[0]
            self.lot_id = data_set.last_data([header.I_LOT_ID])[0]
            
            self.tab_pitch = data_set.last_data([header.I_TAB_PITCH])[0]
            self.tab_width = data_set.last_data([header.I_TAB_WIDTH])[0]
            # ㅊㅇㅇ 레이저 노칭 검사 데이터 추가 (X방향)
            if header.I_TAB_SIDE not in self.data_set.column_name :
                 self.tab_side = 0
            else : self.tab_side = self.data_set.last_data([header.I_TAB_SIDE])[0]
            
            if header.I_TOP_COATING not in self.data_set.column_name :
                self.top_coating = 0
            else : self.top_coating = data_set.last_data([header.I_TOP_COATING])[0]
            
            if header.I_BOTTOM_COATING not in self.data_set.column_name :
                self.bottom_coating = 0
            else : self.bottom_coating = data_set.last_data([header.I_BOTTOM_COATING])[0]
            
            if header.I_TOP_FRONT_CUTTING_HEIGHT not in self.data_set.column_name :
                self.top_front_cutting_height = 0
            else : self.top_front_cutting_height = data_set.last_data([header.I_TOP_FRONT_CUTTING_HEIGHT])[0]
            
            if header.I_TOP_BACK_CUTTING_HEIGHT not in self.data_set.column_name :
                self.top_back_cutting_height = 0
            else : self.top_back_cutting_height = data_set.last_data([header.I_TOP_BACK_CUTTING_HEIGHT])[0]
            
            if header.I_BOTTOM_FRONT_CUTTING_HEIGHT not in self.data_set.column_name :
                self.bottom_front_cutting_height = 0
            else : self.bottom_front_cutting_height = data_set.last_data([header.I_BOTTOM_FRONT_CUTTING_HEIGHT])[0]

            if header.I_BOTTOM_BACK_CUTTING_HEIGHT not in self.data_set.column_name :
                self.bottom_back_cutting_height = 0
            else : self.bottom_back_cutting_height = data_set.last_data([header.I_BOTTOM_BACK_CUTTING_HEIGHT])[0]            
            
            self.offset_direction = header.EPC_DIRECTION                   # EPC수동보정 "+" 버튼을 눌렀을 때, 1: OP방향, -1: MC방향

            self.I_vision_input_time = data_set.recent_row_data([header.I_VISION_INPUT_TIME]) 
            self.I_vision_output_time = data_set.recent_row_data([header.I_VISION_OUTPUT_TIME])
            self.I_process_direction = data_set.recent_row_data([header.I_PROCESS_DIRECTION])
            self.I_judge = data_set.recent_row_data([header.I_JUDGE])
            self.I_appearance_judge_result = data_set.recent_row_data([header.I_APPEARANCE_JUDGE_RESULT])
            self.I_dimension_judge_result = data_set.recent_row_data([header.I_DIMENSION_JUDGE_RESULT]) 
            self.I_lot_id = data_set.recent_row_data([header.I_LOT_ID]) 
            self.I_cell_no = data_set.recent_row_data([header.I_CELL_NO])

            self.I_tab_pitch = data_set.recent_row_data([header.I_TAB_PITCH])
            self.I_tab_width = data_set.recent_row_data([header.I_TAB_WIDTH])

            # ㅊㅇㅇ 레이저 노칭 검사 데이터 추가 (X방향)
            if header.I_TAB_SIDE not in self.data_set.column_name :
                 self.I_tab_side = np.zeros(len(self.data_set.raw_data)).reshape(len(self.data_set.raw_data),1)
            else : self.I_tab_side = self.data_set.recent_row_data([header.I_TAB_SIDE])            

            if header.I_TOP_COATING not in self.data_set.column_name :
                self.I_top_coating = np.zeros(len(self.data_set.raw_data)).reshape(len(self.data_set.raw_data),1)
            else : self.I_top_coating = data_set.recent_row_data([header.I_TOP_COATING])

            if header.I_BOTTOM_COATING not in self.data_set.column_name :
                self.I_bottom_coating = np.zeros(len(self.data_set.raw_data)).reshape(len(self.data_set.raw_data),1)
            else : self.I_bottom_coating = data_set.recent_row_data([header.I_BOTTOM_COATING])
            
            self.I_tab_height = data_set.recent_row_data([header.I_TAB_HEIGHT])
            self.I_length = data_set.recent_row_data([header.I_LENGTH])

            if header.I_TOP_FRONT_CUTTING_HEIGHT not in self.data_set.column_name :
                self.I_top_front_cutting_height = np.zeros(len(self.data_set.raw_data)).reshape(len(self.data_set.raw_data),1)
            else : self.I_top_front_cutting_height = data_set.recent_row_data([header.I_TOP_FRONT_CUTTING_HEIGHT])

            if header.I_TOP_BACK_CUTTING_HEIGHT not in self.data_set.column_name :
                self.I_top_back_cutting_height = np.zeros(len(self.data_set.raw_data)).reshape(len(self.data_set.raw_data),1)
            else : self.I_top_back_cutting_height = data_set.recent_row_data([header.I_TOP_BACK_CUTTING_HEIGHT])
            
            if header.I_BOTTOM_FRONT_CUTTING_HEIGHT not in self.data_set.column_name :
                self.I_bottom_front_cutting_height = np.zeros(len(self.data_set.raw_data)).reshape(len(self.data_set.raw_data),1)
            else : self.I_bottom_front_cutting_height = data_set.recent_row_data([header.I_BOTTOM_FRONT_CUTTING_HEIGHT])

            if header.I_BOTTOM_BACK_CUTTING_HEIGHT not in self.data_set.column_name :
                self.I_bottom_back_cutting_height = np.zeros(len(self.data_set.raw_data)).reshape(len(self.data_set.raw_data),1)
            else : self.I_bottom_back_cutting_height = data_set.recent_row_data([header.I_BOTTOM_BACK_CUTTING_HEIGHT])

            if header.I_ROI_MEAN_PITCH not in self.data_set.column_name :
                self.I_roi_mean_pitch = np.zeros(len(self.data_set.raw_data)).reshape(len(self.data_set.raw_data),1)
            else : self.I_roi_mean_pitch = data_set.recent_row_data([header.I_ROI_MEAN_PITCH]) 

            # 어깨선 항목 확인
            dm.shoulder_line = utility.shulder_line_check(self.top_coating, self.bottom_coating, self.top_front_cutting_height, self.top_back_cutting_height)
            utility.log_write(f"Shoulder line: {dm.shoulder_line}", name='cl_vision', delay=60)
            
            # ㅊㅇㅇ
            self.notching_side_check()
            
            # Lot Chage 확인
            self.lot_change_check()
            
            if dm.shoulder_line:
                self.data_ready = True
            else:
                self.data_ready = False
            
        except Exception as e:
            utility.log_write_by_level("Notch Vision data update 에러...{}".format(e),level='critical', delay=10) 
            utility.log_write(traceback.format_exc(), name='cl_vision', delay=60)


    def lot_change_check(self):
        if (self.prev_lot_id != None) and (self.prev_lot_id != self.lot_id):
            dm.lot_change = True
            utility.log_write(f"{self.prev_lot_id}에서 {self.lot_id}로 Lot ID가 변경되었습니다.")
        else:
            dm.lot_change = False
        self.prev_lot_id = self.lot_id


    # ㅊㅇㅇ - shulder_line_check()를 이걸로 대체 (레이저 노칭 case까지 포함)
    def notching_side_check(self):

        self.notching_side = None

        # Cutting Height
        if (self.top_front_cutting_height) and (self.top_back_cutting_height):

            self.I_top_shulder_line = self.I_top_front_cutting_height
            self.I_back_shulder_line = self.I_top_back_cutting_height
            
            self.top_shulder_line = self.top_front_cutting_height
            self.back_shulder_line = self.top_back_cutting_height

            if (self.bottom_front_cutting_height) and (self.bottom_back_cutting_height):
                self.notching_side = "BOTH"
            else : self.notching_side = "SINGLE"

            self.offset_direction *= -1
            
        # shoulder line
        elif (self.top_coating) and (self.bottom_coating):
            self.I_top_shulder_line = self.I_top_coating
            self.I_back_shulder_line = self.I_bottom_coating
            
            self.top_shulder_line = self.top_coating
            self.back_shulder_line = self.bottom_coating
            
            self.notching_side = "SINGLE"

            
        
            
            
        
        

        
        
        
