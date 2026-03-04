import os
import shutil
import header
import utility
import traceback
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from glob import glob
import plotly.express as px
import plotly.io as pio
import plotly.graph_objs as go
from plotly.subplots import make_subplots

import data_memory as dm

import warnings
warnings.filterwarnings("ignore")

class PLOT():
    def __init__(self):
        
        self.cavity_num = dm.cavity_num
        
        self.tch_usl = header.SPEC_TCH_USL
        self.tch_ref = header.SPEC_TCH_REF
        self.tch_lsl = header.SPEC_TCH_LSL
        
        self.bch_usl = header.SPEC_BCH_USL
        self.bch_ref = header.SPEC_BCH_REF
        self.bch_lsl = header.SPEC_BCH_LSL

        self.tp_usl = header.SPEC_TP_USL
        self.tp_ref = header.SPEC_TP_REF
        self.tp_lsl = header.SPEC_TP_LSL

        self.tw_usl = header.SPEC_TW_USL
        self.tw_ref = header.SPEC_TW_REF
        self.tw_lsl = header.SPEC_TW_LSL

        self.ts_usl = header.SPEC_TS_USL
        self.ts_ref = header.SPEC_TS_REF
        self.ts_lsl = header.SPEC_TS_LSL
    
        # 이미지 폴더 결과 저장 경로
        sub_folder = datetime.now().strftime('%Y-%m-%d')
        
        # ROI_MEAN_PITCH Plot 저장 폴더 경로 생성
        self.plot_dir_name = os.path.join(f'{header.CSV_SAVE_PLOT}', sub_folder)
        if not (os.path.exists(self.plot_dir_name)):
            os.makedirs(self.plot_dir_name)
            
        self.read_csv_file()
        
    def read_csv_file(self):
        try:
            self.data_ready = False
            
            if not self.cavity_num:
                if (header.MACHINE_TYPE == 'MOLD'):
                    utility.log_write('Cavity 갯수가 정의되지 않았습니다.')
                    return

            # 현재 시간 vision file 읽기
            formatted_day = datetime.now().strftime("%Y%m%d")
            
            #!테스트 용도
            # formatted_day = '20240813'
            
            vision_file_path = os.path.join(f"{header.CSV_FILE_PATH_VISION}", "**", f'I_NND_Vision_{formatted_day}*.csv')
            vision_file_list = glob(vision_file_path, recursive=True)
            
            plc_file_path = os.path.join(f"{header.CSV_FILE_PATH_PLC}", "**", f'I_NND_PLC_{formatted_day}*.csv')
            plc_file_list = glob(plc_file_path, recursive=True)
            
            if len(plc_file_list)==0 or len(vision_file_list)==0:
                utility.log_write('PLC 혹은 Vision 파일이 존재하지 않습니다.')
                return 
            
            vision_file_list = sorted(vision_file_list)[-2:] # 최근 2시간 파일 열기!
            vision_map = map(self.csv_safe_reader, vision_file_list)
            vision_df = pd.concat(vision_map, ignore_index=True)
            
            plc_file_list = sorted(plc_file_list)[-2:] # 최근 2시간 파일 열기!
            plc_map = map(self.csv_safe_reader, plc_file_list)
            plc_df = pd.concat(plc_map, ignore_index=True)
            
            plc_df['PLC_TIME'] = pd.to_datetime(plc_df['TIME'], format='%Y%m%d%H%M%S%f', errors='coerce')
            vision_df['Vision_TIME'] = pd.to_datetime(vision_df['TIME'], format='%Y%m%d%H%M%S%f', errors='coerce')

            # ㅊㅇㅇ - 시뮬레이션용    
            # plc_df['PLC_TIME'] = pd.to_datetime(plc_df['TIME'], errors='coerce')
            # vision_df['Vision_TIME'] = pd.to_datetime(vision_df['VISION_INPUT_TIME'], errors='coerce')

            self.lot_id = vision_df['LOT_ID'].unique()[-2]
            
            vision_df = vision_df[vision_df['LOT_ID']==self.lot_id]
            vision_df.sort_values('CELL_NO',inplace=True)
            vision_df = vision_df.reset_index(drop=True)
            ##########################################################
            
            
            
            # Vision 및 PLC 데이터 MERGE!!!
            pp = plc_df[(plc_df['PLC_TIME'] >= vision_df['Vision_TIME'].min()-pd.Timedelta('10s')) 
                        & (plc_df['PLC_TIME'] < vision_df['Vision_TIME'].max()+pd.Timedelta('10s'))
                        & (plc_df['M_CELL_COUNT']>=vision_df['CELL_NO'][0])
                        & (plc_df['M_CELL_COUNT']<=vision_df['CELL_NO'][len(vision_df)-1])].reset_index(drop=True)

            pp = pp[['M_CELL_COUNT','X_BUTTON','Y_BUTTON','LOT_CHANGE_MODE','ELECTRODE_BREAK_MODE']]
            pp = pp.groupby((pp['M_CELL_COUNT'].diff() != 0).cumsum().values, sort=False, as_index=False).agg('first')
            pp.sort_values('M_CELL_COUNT', inplace=True)
            
            self.result_df = pd.merge(vision_df, pp, left_on='CELL_NO', right_on='M_CELL_COUNT', how='left')
            self.result_df.drop(['M_CELL_COUNT'],axis=1, inplace=True)
            self.result_df = self.result_df.ffill().bfill()
            ##########################################################


            # 어깨선 항목 확인
            top_coating = sum(self.result_df['TOP_COATING']) 
            bottom_coating = sum(self.result_df['BOTTOM_COATING'])
            shoulder_line = utility.shulder_line_check(top_coating, bottom_coating)
            utility.log_write(f"Graph Process - Shoulder line: {shoulder_line}")
            utility.log_write(f'Graph Process - Cavity Nun: {self.cavity_num}')
            self.get_shulder_line(shoulder_line)
            

            # NG Count 계산하기
            self.count_ng = utility.NG_count(self.result_df, 'TOP_SHOULDER_LINE', 'BACK_SHOULDER_LINE', self.tch_usl, self.tch_lsl)
            utility.log_write(f"Graph Process - Count NG: {self.count_ng}")

            if 'BOTTOM_FRONT_CUTTING_HEIGHT' in self.result_df.columns :
                self.count_ng_bch = utility.NG_count(self.result_df, 'BOTTOM_FRONT_CUTTING_HEIGHT','BOTTOM_BACK_CUTTING_HEIGHT', self.bch_usl, self.bch_lsl)
                utility.log_write(f"Graph Process - Count NG: {self.count_ng_bch}")
            else : self.count_ng_bch = 0
            

            # Cpk 계산하기
            cpk_df = self.result_df[(self.result_df['SHOULDER_LINE']>=(self.tch_lsl-1)) & (self.result_df['SHOULDER_LINE']<=(self.tch_usl+1))]
            tch_top_cpk = utility.Cpk_Calc(cpk_df, "TOP_SHOULDER_LINE", self.tch_usl, self.tch_lsl)
            tch_back_cpk = utility.Cpk_Calc(cpk_df, "BACK_SHOULDER_LINE", self.tch_usl, self.tch_lsl)
            self.cpk_value = round((tch_top_cpk + tch_back_cpk)/2, 2)
            utility.log_write(f"Graph Process - Cpk Value: {self.cpk_value}")
            

            # Lot ID 기준 Start Datetime ~ End Datetime 
            self.date_period = f"{str(self.result_df['TIME'].min())[:-3]} ~ {str(self.result_df['TIME'].max())[:-3]}"
            utility.log_write(f"Graph Process - Date Period: {self.date_period}")
            

            # X_BUTTON, Y_BUTTON 켜진(ON) 구간 구하기
            self.X_BUTTON = self.get_period_data('X_BUTTON')
            self.Y_BUTTON = self.get_period_data('Y_BUTTON')
            self.LOT_CHANGE_MODE = self.get_period_data('LOT_CHANGE_MODE')
            self.ELECTRODE_BREAK_MODE = self.get_period_data('ELECTRODE_BREAK_MODE')
            ############################################################
        

            self.data_ready = True
                
        except FileNotFoundError as e:
            utility.log_write_by_level(f"Graph 그리기 위한 {self.formatted_day} 파일을 찾을 수가 없습니다. {e}", level='debug')
    
        except Exception as ex:
            dm.lot_change = False
            utility.log_write(f"Graph read file error occured! : {ex}")
            utility.log_write_by_level("Graph read file error occured! :{}".format(traceback.format_exc()), level='critical')
            

    @staticmethod
    def csv_safe_reader(filename, table_name='graph'): ## PIE와의 충돌을 피하기 위해, 파일을 복사해서 사용한다.

        try :

            temp_filename = 'dont_touch/temp' + '_' + table_name + '.csv'
            shutil.copyfile(filename, dst=temp_filename)
            dataset = pd.read_csv(temp_filename, on_bad_lines='skip', encoding_errors='ignore') # 0929 파일럿 음극 vision error line 존재

        except Exception as ex :
            utility.log_write_by_level("csv_safe_reader 실패...{}".format(ex),level='critical')
            dataset = None

        return(dataset)

    @staticmethod
    def horizontal_plot(fig, row, col, min_val, max_val, value, color):     
        # 수평선을 점선으로 추가
        fig.add_shape(
            type='line',
            x0=min_val,
            y0=value,
            x1=max_val,
            y1=value,
            line=dict(
                color=color,
                width=2,
                dash='dash',  # 점선 스타일
            ),
            row=row,
            col=col
        )
        
    @staticmethod    
    def add_shading(fig, prev_x, post_x, row, color='LightSalmon'):
        fig.add_shape(
                    type="rect",
                    x0=prev_x, x1=post_x, y0=-100, y1=1000, xref="x", yref="paper",
                    fillcolor=color, opacity=0.3, layer='below', line_width=0,
                    row=row, col=1
                )
    

    @staticmethod 
    def add_legend(fig, name, color='LightSalmon'):
        fig.add_trace(go.Scatter(
            x=[None],
            y=[None],
            mode='markers',
            marker=dict(
                size=10,
                color=color,
                line=dict(width=2, color=color)
            ),
            showlegend=True,
            name=name
        ))


    def make_plot(self):

        if header.MACHINE_TYPE == "MOLD" :
            self.make_cavity_plot()
            self.make_inspection_plot()

        elif header.MACHINE_TYPE == "LASER" :
            self.laser_make_x_plot()
            self.laser_make_y_plot()

        utility.log_write('Graph 차트 멀티프로세싱 작업 종료')
        
        
    def get_period_data(self, col):
        group_col = f'{col}_GROUP'
        self.result_df[group_col] = (self.result_df[col].diff()!=0).cumsum()
        self.period_df = self.result_df.groupby([group_col, col])[['CELL_NO']].first().reset_index()
        
        self.period_df['POST_CELL_NO'] = self.period_df['CELL_NO'].shift(-1)-1
        self.period_df['POST_CELL_NO'].fillna(self.result_df['CELL_NO'].iloc[-1], inplace=True)
        self.period_df.rename(columns={'CELL_NO':'PREV_CELL_NO'}, inplace=True)
        self.period_df = self.period_df[self.period_df[col]==1].reset_index(drop=True)
        return self.period_df


    def make_cavity_plot(self):
        try:
            utility.log_write("Graph Process - Make Cavity Plot Started!")
            # 서브플롯 생성
            # 행은 2로 고정하고, 열은 num // 2로 설정
            rows = 2
            cols = (self.cavity_num + 1) // 2  # 올림 연산을 위해 (cavity_num + 1) // 2 사용
            
            var_list = list()
            
            # 서브플롯 생성
            subplot_titles = [f"Cavity {i+1}" for i in range(self.cavity_num)]
            fig = make_subplots(rows=rows, cols=cols, subplot_titles=subplot_titles)
            
            # 예제 데이터 생성 (각 플롯에 대한 y 값을 다르게 설정)
            for i in range(self.cavity_num):
                temp_df = self.result_df[self.result_df['CELL_NO'] % self.cavity_num == i]
                
                sub_x = temp_df['CELL_NO'].values
                sub_y = temp_df['ROI_MEAN_PITCH'].values
                variation = np.round(sub_y.var(), 3)
                
                var_list.append(variation)
                
                row = (i // cols) + 1
                col = (i % cols) + 1
                fig.add_trace(go.Scatter(x=sub_x, y=sub_y, mode='lines', name=f'Cavity {i+1} : {variation}'), row=row, col=col)

                # SPEC 선 그리기
                self.horizontal_plot(fig, row, col, min_val=min(sub_x), max_val=max(sub_x), value=self.tp_usl, color='Red')
                self.horizontal_plot(fig, row, col, min_val=min(sub_x), max_val=max(sub_x), value=self.tp_lsl, color='Red')
                self.horizontal_plot(fig, row, col, min_val=min(sub_x), max_val=max(sub_x), value=self.tp_ref, color='blue')
            
            # y축 범례 고정하기
            fig.update_yaxes(range=[self.tp_lsl-0.5, self.tp_usl+0.5], tickvals=[self.tp_lsl-0.35, self.tp_lsl, self.tp_ref, self.tp_usl, self.tp_usl+0.35])
        
            # 레이아웃 업데이트
            fig.update_layout(title_text=f"[{self.lot_id}] : {self.date_period}")

            # 차트 출력
            # fig.show()
            var_diff = np.round(max(var_list) - min(var_list), 3)
            img_save_path = os.path.join(self.plot_dir_name, f'[{self.lot_id}]Max-Min_{var_diff}_Cavity_Plot.html')
            fig.write_html(img_save_path)
            utility.log_write(f"Cavity Plot Saved To {img_save_path}")

        except Exception as ex:
            utility.log_write(f"Make Cavity Plot Error : {ex}")
            utility.log_write_by_level("Make Cavity Plot Error :{}".format(traceback.format_exc()), level='critical')

    def make_inspection_plot(self):
        try:
            # 서브플롯 생성
            fig = make_subplots(rows=3, cols=1, subplot_titles=(f"TOP/BACK_SHOULDER_LINE (NG Count: {self.count_ng})", "TAB_PITCH", "ROI_MEAN_PITCH"))
            cols = ['TOP_SHOULDER_LINE','BACK_SHOULDER_LINE','TAB_PITCH','ROI_MEAN_PITCH']

            for i, col in enumerate(cols):
                if (i == 0) or (i == 1):
                    i=1
                    self.horizontal_plot(fig, row=i, col=1, min_val=min(self.result_df['CELL_NO']), max_val=max(self.result_df['CELL_NO']), value=self.tch_usl, color='Red')
                    self.horizontal_plot(fig, row=i, col=1, min_val=min(self.result_df['CELL_NO']), max_val=max(self.result_df['CELL_NO']), value=self.tch_lsl, color='Red')
                    self.horizontal_plot(fig, row=i, col=1, min_val=min(self.result_df['CELL_NO']), max_val=max(self.result_df['CELL_NO']), value=self.tch_ref, color='blue')

                    # y축 범례 고정하기
                    fig.update_yaxes(range=[self.tch_lsl-0.5, self.tch_usl+0.5], tickvals=[self.tch_lsl-0.35, self.tch_lsl, self.tch_ref, self.tch_usl, self.tch_usl+0.35], row=i, col=1)
            
                else:
                    self.horizontal_plot(fig, row=i, col=1, min_val=min(self.result_df['CELL_NO']), max_val=max(self.result_df['CELL_NO']), value=self.tp_lsl, color='Red')
                    self.horizontal_plot(fig, row=i, col=1, min_val=min(self.result_df['CELL_NO']), max_val=max(self.result_df['CELL_NO']), value=self.tp_ref, color='blue')
                    self.horizontal_plot(fig, row=i, col=1, min_val=min(self.result_df['CELL_NO']), max_val=max(self.result_df['CELL_NO']), value=self.tp_usl, color='Red')
                    
                    # y축 범례 고정하기
                    fig.update_yaxes(range=[self.tp_lsl-0.5, self.tp_usl+0.5], tickvals=[self.tp_lsl-0.35, self.tp_lsl, self.tp_ref, self.tp_usl, self.tp_usl+0.35], row=i, col=1)
            
                
                fig.add_trace(
                    go.Scatter(x=self.result_df['CELL_NO'], y=self.result_df[col], mode='lines', name=col),
                    row=i, col=1
                )
                
            # 재료 교체 구간(yellow), 파단 구간(purple) 음영으로 표현하기
            lot_chage_color = 'yellow'
            break_mode_color =  'purple'
            
            for color, group_df in zip([lot_chage_color, break_mode_color], [self.LOT_CHANGE_MODE, self.ELECTRODE_BREAK_MODE]):
                for row in range(1 , 4):
                    for i in range(len(group_df)):
                        self.add_shading(fig, group_df.loc[i, 'PREV_CELL_NO'], group_df.loc[i, 'POST_CELL_NO'], row=row, color=color)
                        
            # 자동보정 On 구간 음영으로 표현하기
            for i in range(len(self.Y_BUTTON)):
                self.add_shading(fig, self.Y_BUTTON.loc[i, 'PREV_CELL_NO'], self.Y_BUTTON.loc[i, 'POST_CELL_NO'], row=1)
                
            for i in range(len(self.X_BUTTON)):
                self.add_shading(fig, self.X_BUTTON.loc[i, 'PREV_CELL_NO'], self.X_BUTTON.loc[i, 'POST_CELL_NO'], row=2)
                
            for i in range(len(self.X_BUTTON)):
                self.add_shading(fig, self.X_BUTTON.loc[i, 'PREV_CELL_NO'], self.X_BUTTON.loc[i, 'POST_CELL_NO'], row=3)    
                
            self.add_legend(fig, name="LOT_CHANGE_MODE", color=lot_chage_color)
            self.add_legend(fig, name="ELECTRODE_BREAK_MODE", color=break_mode_color)
            self.add_legend(fig, name="X_BUTTON / Y_BUTTON")
            
            # 레이아웃 업데이트
            fig.update_layout(title_text=f"[{self.lot_id}] : {self.date_period}")

            # 차트 출력
            insp_img_save_path = os.path.join(self.plot_dir_name, f'[{self.lot_id}]Inspection_NG_{self.count_ng}_Cpk_{self.cpk_value}_Plot.html')
            fig.write_html(insp_img_save_path)
            utility.log_write(f"Inspection Plot Saved To {insp_img_save_path}")
        except Exception as ex:
            utility.log_write(f"Make Inspection Plot Error : {ex}")
            utility.log_write_by_level("Make Inspection Plot Error :{}".format(traceback.format_exc()), level='critical')

    def laser_make_x_plot(self):
        try:
            # 서브플롯 생성
            fig = make_subplots(rows=3, cols=1, subplot_titles=('TAB_PITCH','TAB_WIDTH','TAB_SIDE'))
            cols = ['TAB_PITCH','TAB_WIDTH','TAB_SIDE']

            usl_list=[self.tp_usl, self.tw_usl, self.ts_usl]
            lsl_list=[self.tp_lsl, self.tw_lsl, self.ts_lsl]
            ref_list=[self.tp_ref, self.tw_ref, self.ts_ref]
            
            for i, col in enumerate(cols):

                if col not in self.result_df.columns:
                    continue

                usl=usl_list[i]
                lsl=lsl_list[i]
                ref=ref_list[i]

                self.horizontal_plot(fig, row=i+1, col=1, min_val=min(self.result_df['CELL_NO']), max_val=max(self.result_df['CELL_NO']), value=usl, color='Red')
                self.horizontal_plot(fig, row=i+1, col=1, min_val=min(self.result_df['CELL_NO']), max_val=max(self.result_df['CELL_NO']), value=lsl, color='Red')
                self.horizontal_plot(fig, row=i+1, col=1, min_val=min(self.result_df['CELL_NO']), max_val=max(self.result_df['CELL_NO']), value=ref, color='blue')
                fig.update_yaxes(range=[lsl-0.5, usl+0.5], tickvals=[lsl-0.35, lsl, ref, usl, usl+0.35], row=i+1, col=1)

                fig.add_trace(
                    go.Scatter(x=self.result_df['CELL_NO'], y=self.result_df[col], mode='lines', name=col),
                    row=i+1, col=1
                )

            # 재료 교체 구간(yellow), 파단 구간(purple) 음영으로 표현하기
            lot_chage_color = 'yellow'
            break_mode_color =  'purple'
            
            for color, group_df in zip([lot_chage_color, break_mode_color], [self.LOT_CHANGE_MODE, self.ELECTRODE_BREAK_MODE]):
                for row in range(1 , 4):
                    for i in range(len(group_df)):
                        self.add_shading(fig, group_df.loc[i, 'PREV_CELL_NO'], group_df.loc[i, 'POST_CELL_NO'], row=row, color=color)

            # 자동보정 On 구간 음영으로 표현하기
            for i in range(len(self.X_BUTTON)):
                self.add_shading(fig, self.X_BUTTON.loc[i, 'PREV_CELL_NO'], self.X_BUTTON.loc[i, 'POST_CELL_NO'], row=1)
                
            for i in range(len(self.X_BUTTON)):
                self.add_shading(fig, self.X_BUTTON.loc[i, 'PREV_CELL_NO'], self.X_BUTTON.loc[i, 'POST_CELL_NO'], row=2)

            for i in range(len(self.X_BUTTON)):
                self.add_shading(fig, self.X_BUTTON.loc[i, 'PREV_CELL_NO'], self.X_BUTTON.loc[i, 'POST_CELL_NO'], row=3)

            self.add_legend(fig, name="LOT_CHANGE_MODE", color=lot_chage_color)
            self.add_legend(fig, name="ELECTRODE_BREAK_MODE", color=break_mode_color)
            self.add_legend(fig, name="X_BUTTON / Y_BUTTON")
            
            # 레이아웃 업데이트
            fig.update_layout(title_text=f"[{self.lot_id}] : {self.date_period}")

            # 차트 출력
            insp_img_save_path = os.path.join(self.plot_dir_name, f'[{self.lot_id}]_X_Plot.html')
            fig.write_html(insp_img_save_path)
            utility.log_write(f"X Plot Saved To {insp_img_save_path}")

        except Exception as ex:
            utility.log_write(f"Make x plot laser Error : {ex}")
            utility.log_write_by_level("Make x plot laser Error :{}".format(traceback.format_exc()), level='critical')

    def laser_make_y_plot(self):
        try:
            # 서브플롯 생성
            fig = make_subplots(rows=2, cols=1, subplot_titles=(f"TAB_CUTTING_HEIGHT (NG Count: {self.count_ng})", f"BOTTOM_CUTTING_HEIGHT (NG Count: {self.count_ng_bch})"))
            cols = ['TOP_SHOULDER_LINE','BACK_SHOULDER_LINE','BOTTOM_FRONT_CUTTING_HEIGHT','BOTTOM_BACK_CUTTING_HEIGHT']

            for i, col in enumerate(cols):

                if col not in self.result_df.columns:
                    continue

                if (i == 0) or (i == 1):
                    
                    i=1
                    self.horizontal_plot(fig, row=i, col=1, min_val=min(self.result_df['CELL_NO']), max_val=max(self.result_df['CELL_NO']), value=self.tch_usl, color='Red')
                    self.horizontal_plot(fig, row=i, col=1, min_val=min(self.result_df['CELL_NO']), max_val=max(self.result_df['CELL_NO']), value=self.tch_lsl, color='Red')
                    self.horizontal_plot(fig, row=i, col=1, min_val=min(self.result_df['CELL_NO']), max_val=max(self.result_df['CELL_NO']), value=self.tch_ref, color='blue')

                    # y축 범례 고정하기
                    fig.update_yaxes(range=[self.tch_lsl-0.5, self.tch_usl+0.5], tickvals=[self.tch_lsl-0.35, self.tch_lsl, self.tch_ref, self.tch_usl, self.tch_usl+0.35], row=i, col=1)
            
                else:

                    i=2
                    self.horizontal_plot(fig, row=i, col=1, min_val=min(self.result_df['CELL_NO']), max_val=max(self.result_df['CELL_NO']), value=self.bch_lsl, color='Red')
                    self.horizontal_plot(fig, row=i, col=1, min_val=min(self.result_df['CELL_NO']), max_val=max(self.result_df['CELL_NO']), value=self.bch_ref, color='blue')
                    self.horizontal_plot(fig, row=i, col=1, min_val=min(self.result_df['CELL_NO']), max_val=max(self.result_df['CELL_NO']), value=self.bch_usl, color='Red')
                    
                    # y축 범례 고정하기
                    fig.update_yaxes(range=[self.bch_lsl-0.5, self.bch_usl+0.5], tickvals=[self.bch_lsl-0.35, self.bch_lsl, self.bch_ref, self.bch_usl, self.bch_usl+0.35], row=i, col=1)
            
                fig.add_trace(
                    go.Scatter(x=self.result_df['CELL_NO'], y=self.result_df[col], mode='lines', name=col),
                    row=i, col=1
                )
                
            # 재료 교체 구간(yellow), 파단 구간(purple) 음영으로 표현하기
            lot_chage_color = 'yellow'
            break_mode_color =  'purple'
            
            for color, group_df in zip([lot_chage_color, break_mode_color], [self.LOT_CHANGE_MODE, self.ELECTRODE_BREAK_MODE]):
                for row in range(1 , 3):
                    for i in range(len(group_df)):
                        self.add_shading(fig, group_df.loc[i, 'PREV_CELL_NO'], group_df.loc[i, 'POST_CELL_NO'], row=row, color=color)
                        
            # 자동보정 On 구간 음영으로 표현하기
            for i in range(len(self.Y_BUTTON)):
                self.add_shading(fig, self.Y_BUTTON.loc[i, 'PREV_CELL_NO'], self.Y_BUTTON.loc[i, 'POST_CELL_NO'], row=1)
                
            for i in range(len(self.Y_BUTTON)):
                self.add_shading(fig, self.Y_BUTTON.loc[i, 'PREV_CELL_NO'], self.Y_BUTTON.loc[i, 'POST_CELL_NO'], row=2)
                
            self.add_legend(fig, name="LOT_CHANGE_MODE", color=lot_chage_color)
            self.add_legend(fig, name="ELECTRODE_BREAK_MODE", color=break_mode_color)
            self.add_legend(fig, name="X_BUTTON / Y_BUTTON")
            
            # 레이아웃 업데이트
            fig.update_layout(title_text=f"[{self.lot_id}] : {self.date_period}")

            # 차트 출력
            insp_img_save_path = os.path.join(self.plot_dir_name, f'[{self.lot_id}]_Y_Plot.html')
            fig.write_html(insp_img_save_path)
            utility.log_write(f"Y Plot Saved To {insp_img_save_path}")
            
        except Exception as ex:
            utility.log_write(f"Make y plot laser Error : {ex}")
            utility.log_write_by_level("Make y plot laser Error :{}".format(traceback.format_exc()), level='critical')
            
        
    def get_shulder_line(self, mode):
        try:
            # Cutting Height
            if mode == "TCH":
                self.result_df['TOP_SHOULDER_LINE'] = self.result_df['TOP_FRONT_CUTTING_HEIGHT']
                self.result_df['BACK_SHOULDER_LINE'] = self.result_df['TOP_BACK_CUTTING_HEIGHT']
                self.result_df['SHOULDER_LINE'] = round(self.result_df[['TOP_FRONT_CUTTING_HEIGHT','TOP_BACK_CUTTING_HEIGHT']].mean(axis=1), 3)
            # shoulder line
            elif mode == "TN":
                self.result_df['TOP_SHOULDER_LINE'] = self.result_df['TOP_COATING']
                self.result_df['BACK_SHOULDER_LINE'] = self.result_df['BOTTOM_COATING']
                self.result_df['SHOULDER_LINE'] = round(self.result_df[['TOP_COATING','BOTTOM_COATING']].mean(axis=1), 3)
        except Exception as ex:
            utility.log_write_by_level("Get Shulder Line Error :{}".format(traceback.format_exc()), level='critical')
