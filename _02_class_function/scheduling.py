import os
import header
import traceback
from glob import glob 
from datetime import datetime, timedelta
import pandas as pd
import utility
import data_memory as dm
from collections import Counter

import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
    
import warnings
warnings.filterwarnings("ignore")

class OPTIMIZATION_ANALYSIS():
    def __init__(self):
        # 하루 전 계산
        self.one_day_before = datetime.now() - timedelta(days=header.DAYS_AGO) 
        # 원하는 문자열 형식으로 변환
        self.formatted_day = self.one_day_before.strftime("%Y%m%d")
        
        # #! 테스트 용도
        # self.formatted_day = '20240807'
        
        # csv파일로 결과 저장
        sub_folder = self.one_day_before.strftime("%Y-%m-%d")
        
        # CTP-CTQ Correlation Anlaysis
        self.corr_dir_name = os.path.join(f'{header.CSV_SAVE_EPC_CORR}', sub_folder)
        if not (os.path.exists(self.corr_dir_name)):
            os.makedirs(self.corr_dir_name)
        
        file_name = f"O_NND_EPC_CORR_{self.formatted_day}.csv"
        self.corr_file_path = os.path.normpath(os.path.join(self.corr_dir_name, file_name))
        
        # Gain Optimization Anlaysis
        self.gain_dir_name = os.path.join(f'{header.CSV_SAVE_GAIN_OPTIMIZATION}', sub_folder)
        if not (os.path.exists(self.gain_dir_name)):
            os.makedirs(self.gain_dir_name)
        
        file_name = f"O_NND_GAIN_OPTIMIZAION_{self.formatted_day}.csv"
        self.gain_file_path = os.path.normpath(os.path.join(self.gain_dir_name, file_name))
        
        
        if not (os.path.exists(self.corr_file_path)) or not (os.path.exists(self.gain_file_path)):
            if os.path.exists(self.corr_file_path):
                utility.log_write('CTP-CTQ 상관분석 결과가 이미 존재합니다.')
                self.corr_run = False
                self.gain_run = True
                
            if os.path.exists(self.gain_file_path):
                utility.log_write('Gain 최적화 분석 결과가 이미 존재합니다.')
                self.gain_run = False
                self.corr_run = True
                
            if not (os.path.exists(self.corr_file_path)) and not (os.path.exists(self.gain_file_path)):
                self.gain_run = True
                self.corr_run = True
                
            self.read_csv_file()
        else:
            utility.log_write('CTP-CTQ 상관분석 결과가 이미 존재합니다.')
            utility.log_write('Gain 최적화 분석 결과가 이미 존재합니다.')
            self.data_ready = False



    def read_file(self, file_path):
        return pd.read_csv(file_path, on_bad_lines='skip', encoding='UTF-8', encoding_errors='ignore')


    def read_csv_file(self):
        try:
            self.data_ready = False
            utility.log_write('Batch Analysis를 위한 데이터를 읽고 있는 중입니다...')
            plc_file_path = os.path.join(f"{header.CSV_FILE_PATH_PLC}", "BACKUP", f"*{self.formatted_day}*.csv")
            vision_file_path = os.path.join(f"{header.CSV_FILE_PATH_VISION}", "BACKUP", f"*{self.formatted_day}*.csv")
            
            plc_file_list = glob(plc_file_path)
            vision_file_list = glob(vision_file_path)
            
            utility.log_write(f'{self.formatted_day}의 PLC 파일 수: {len(plc_file_list)}, Vision 파일 수: {len(vision_file_list)}')
            
            if len(plc_file_list)==0:
                utility.log_write('PLC 파일이 존재하지 않습니다.')
                return
            elif len(vision_file_list)==0:
                utility.log_write('Vision 파일이 존재하지 않습니다.')
                return 

            plc_map = map(self.read_file, plc_file_list)
            vision_map = map(self.read_file, vision_file_list)

            
            self.plc_df = pd.concat(plc_map, ignore_index=True)
            self.vision_df = pd.concat(vision_map, ignore_index=True)

            self.plc_df['PLC_TIME'] = pd.to_datetime(self.plc_df['TIME'], format='%Y%m%d%H%M%S%f', errors='coerce')
            self.vision_df['Vision_TIME'] = pd.to_datetime(self.vision_df['TIME'], format='%Y%m%d%H%M%S%f', errors='coerce') 
            
            self.plc_df['EPC_SENSOR_POS'] = self.plc_df['EPC_SENSOR_POS'] / 1000
            self.plc_df['LOT_CHANGE_GUBUN'] = (self.plc_df['LOT_CHANGE_MODE'].diff() != 0).cumsum()
            
            # 어깨선 구하기
            # 어깨선 항목 확인
            top_coating = sum(self.vision_df['TOP_COATING']) 
            bottom_coating = sum(self.vision_df['BOTTOM_COATING'])
            self.shoulder_line = utility.shulder_line_check(top_coating, bottom_coating)
            utility.log_write(f"Scheduling Process - Shoulder line: {self.shoulder_line}")
            self.get_shulder_line()
            
            
            if (len(self.plc_df)>1000) and (len(self.vision_df)>1000):
                self.data_ready = True
                utility.log_write(f"Batch Analysis를 위한 데이터를 모두 읽었습니다.")
            else:
                utility.log_write(f"Batch Analysis를 위한 충분한 데이터가 존재하지 않습니다.")
            
        except FileNotFoundError as e:
            utility.log_write_by_level(f"BACKUP 폴더 내 {self.formatted_day} 날짜 파일을 찾을 수가 없습니다. {e}", level='debug')
    
        except Exception as ex:
            utility.log_write(f"Optimization Analysis Error : {ex}")
            
        
    #^ Tape 붙인 시점 Cell No 기준으로 뒤 10개 Cell 이후 데이터 (재료교체 구간) 
    #  - LOT CHAGE(=1) 구간에서 3개 포인트 기준으로 max값 - min값이 가장 큰 지점을 Tape 붙인 시점(tape_cell_no) 구하기    
    def get_lot_change(self):
        try:
            lot_count = 0
            self.total_lot_chage = list()
            
            lot_chage_gubun = list(self.plc_df[self.plc_df['LOT_CHANGE_MODE']==1]['LOT_CHANGE_GUBUN'].unique())
            
            if len(lot_chage_gubun) > 0:
            
                for lot_change in lot_chage_gubun:
                    pp = self.plc_df[self.plc_df['LOT_CHANGE_GUBUN']==lot_change].reset_index(drop=True)

                    pp.sort_values('M_CELL_COUNT', inplace=True)
                    pp = pp.reset_index(drop=True)

                    vv = self.vision_df[(self.vision_df['Vision_TIME'] >= pp['PLC_TIME'].min()-pd.Timedelta('30s')) 
                                & (self.vision_df['Vision_TIME'] < pp['PLC_TIME'].max()+pd.Timedelta('30s'))
                                & (self.vision_df['CELL_NO']>=pp['M_CELL_COUNT'][0])
                                & (self.vision_df['CELL_NO']<=pp['M_CELL_COUNT'][len(pp)-1])].reset_index(drop=True)
                    
                    
                    if len(vv) > 200:
                        # NG셀은 버리면 중간에 셀이 비워져 있기 때문에, NG셀 다음 OK셀로 값 채워줘서 차이값 계산하는데 영향 받지 않게 하기
                        ng_df = vv[(vv['DIMENSION_JUDGE_RESULT']=='NG') & ((vv['SHOULDER_LINE']<=0) | (vv['SHOULDER_LINE']>=8))]
                        
                        vv.loc[ng_df.index,'SHOULDER_LINE']=np.nan
                        vv['SHOULDER_LINE'] = vv['SHOULDER_LINE'].fillna(method='bfill')
                        
                        vv.sort_values('CELL_NO',inplace=True) 
                        vv = vv.reset_index(drop=True)
                        
                        y_df = pd.DataFrame(vv[['SHOULDER_LINE']].values, index=vv['CELL_NO'], columns=['SHOULDER_LINE'])

                        if len(ng_df) <= 3:
                            window_size = 3
                        else:
                            window_size = len(ng_df)
                        step_size = 1

                        # Tape 붙힌 시점의 Cell No 찾기.
                        y_df_range = y_df.rolling(window=window_size, step=step_size, center=True).max() - y_df.rolling(window=window_size, step=step_size, center=True).min()
                        tape_cell_no = y_df_range[(y_df_range == y_df_range.max().values).all(axis=1)].index[0] + 1

                        
                        # Tape 붙인 시점 Cell No 기준으로 뒤 10개 Cell 가져오기 (재료교체 구간)
                        last_cell_no = list(pp['M_CELL_COUNT'])[-1]
                        vv = self.vision_df[(self.vision_df['Vision_TIME'] >= pp['PLC_TIME'].min()-pd.Timedelta('120s')) 
                                        & (self.vision_df['Vision_TIME'] < pp['PLC_TIME'].max()+pd.Timedelta('120s')) 
                                        & (self.vision_df['CELL_NO']>tape_cell_no + 10) 
                                        & (self.vision_df['CELL_NO']<=last_cell_no)].reset_index(drop=True)

                        vv = vv[(vv['DIMENSION_JUDGE_RESULT']=='OK')]
                        vv.sort_values('CELL_NO',inplace=True) 
                        vv = vv.reset_index(drop=True)
                        
                        y_df = pd.DataFrame(vv[['TOP_SHOULDER_LINE','BACK_SHOULDER_LINE', 'LOT_ID']].values, index=vv['CELL_NO'], columns=['TOP_SHOULDER_LINE','BACK_SHOULDER_LINE', 'LOT_ID'])
                        self.total_lot_chage.append(y_df)
                        lot_count += 1
                        
                utility.log_write(f'{lot_count}개의 재료교체 구간을 찾았습니다.')
            else:
                utility.log_write('재료교체 구간이 존재하지 않습니다.')

        except Exception as ex:
            utility.log_write(f"Get Lot Changed error : {ex}")


    def gain_optimizaion(self):
        try:
            utility.log_write('Gain 최적화 분석 작업 시작')
            self.get_lot_change()
            
            # Parameter
            control_cycle = [30, 25, 20, 15, 10]
            p_gain = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]

            # 각 Case당 구한 best parameter 저장 리스트 -> 나중에 평균낼 것
            best_parameter = dict()

            # data : (Tape+5)~end (약 195개 데이터)
            # data_set : 1개 설비에서 취득한 Lot Change구간 데이터 N개
            # for data in data_set:
            for i, lot_chage_df in enumerate(self.total_lot_chage):
                ng_cnt_org = self.NG_count(lot_chage_df)  # 원본 데이터의 NG 개수
                # print(f"Init NG Count: {ng_cnt_org}")

                best_cc = control_cycle[0]
                best_gain = p_gain[0]

                for cycle in control_cycle:
                    for gain in p_gain:
                        data_sim = self.simulation(lot_chage_df, cycle, gain) # Simulation
                        ng_cnt_sim = self.NG_count(data_sim)  # 원본 데이터의 NG 개수
                        
                        
                        if ng_cnt_sim < ng_cnt_org:
                            best_cc = cycle
                            best_gain = gain
                            # print(f"NG Count: {ng_cnt_sim}")
                            
                if len(lot_chage_df['LOT_ID'].unique())>0:
                    best_parameter[lot_chage_df['LOT_ID'].unique()[0]] = [best_cc, best_gain]
                    # 최빈값 찾기
                    mode = self.find_mode_in_2d_list(best_parameter.values())
                
            utility.log_write(f"best_parameter: {best_parameter}")
            utility.log_write(f'Lot Change Optimal Parameter - Cycle : {mode[0]} / P Gain : {mode[1]}')

            gain_result_df = pd.DataFrame(best_parameter).T
            gain_result_df = gain_result_df.reset_index()
            gain_result_df.columns = ['LOT_ID', 'Control_Cycle', 'Gain']
            
            if len(gain_result_df) > 0:
                gain_result_df.to_csv(self.gain_file_path, index=False)
                utility.log_write(f'{len(gain_result_df)}개 Lot_ID 의 Gain 최적화 결과가 분석되었습니다.')
            else:
                utility.log_write('Gain 최적화 분석 결과가 존재하지 않습니다.')
                
            utility.log_write('Gain 최적화 분석 작업 종료')
            
        except Exception as ex:
            utility.log_write(f"Gain Optimizaion Analysis Error : {ex}")
            utility.log_write_by_level("Gain Optimizaion Analysis Error :{}".format(traceback.format_exc()), level='critical')

    def calculate_corr(self):
        try:
            utility.log_write('CTP-CTQ 상관분석 작업 시작')
            total_valid_list = list()
            
            for lot_id in self.vision_df['LOT_ID'].unique():
            
                vv = self.vision_df[self.vision_df['LOT_ID'] == lot_id][['Vision_TIME', 'JUDGE', 'CELL_NO', 'SHOULDER_LINE']]
                vv.sort_values('CELL_NO',inplace=True)
                
                pp = self.plc_df[['PLC_TIME', 'M_CELL_COUNT', 'EPC_SENSOR_POS']][(self.plc_df['PLC_TIME'] >= vv['Vision_TIME'].min()-pd.Timedelta('10s')) & (self.plc_df['PLC_TIME'] <= vv['Vision_TIME'].max()+pd.Timedelta('10s'))]
                pp = pp.groupby((pp['M_CELL_COUNT'].diff() != 0).cumsum().values, sort=False, as_index=False).agg({'PLC_TIME':'first', 'M_CELL_COUNT': 'first', 'EPC_SENSOR_POS': 'median'})
                pp.sort_values('M_CELL_COUNT', inplace=True)
                
                self.result_df = pd.merge(vv, pp, left_on='CELL_NO', right_on='M_CELL_COUNT', how='left')
                self.result_df = self.result_df[(self.result_df['JUDGE']=='OK')]
                self.result_df = self.result_df.dropna(how='any',axis=0).reset_index(drop=True)
                # self.result_df = self.result_df.groupby('M_CELL_COUNT', sort=False, as_index=False).agg({'CELL_NO': 'first', 'SHOULDER_LINE': 'median', 'M_CELL_COUNT': 'first', 'EPC_SENSOR_POS':'first'})

                if len(self.result_df)==0:
                    continue
                
                self.set_change_flag('EPC_SENSOR_POS', threshold=0.025, term_idx=100)

                best_params, max_corr = self.grid_search(window_sizes=[20], shift_sizes=range(-15, -45, -5))

                if not best_params:
                    continue

                utility.log_write(f"Lot ID: {lot_id}, window_size: {best_params[0]}, shift_size: {best_params[1]}")
        
                self.result_df['ROLLING_SHOULDER_LINE'] = self.result_df['SHOULDER_LINE'].rolling(best_params[0], center=True).median().shift(best_params[1])
                self.result_df = self.result_df.ffill().bfill()
                
                valid_epc_data = self.result_df[(self.result_df['EPC_SENSOR_POS_Flag']==1)].reset_index(drop=True)

                if len(valid_epc_data) > 1:
                    
                    valid_epc_data['Diff_EPC_SENSOR_POS'] = valid_epc_data['EPC_SENSOR_POS'].diff(1)
                    valid_epc_data['Diff_SHOULDER_LINE'] = valid_epc_data['ROLLING_SHOULDER_LINE'].diff(1)

                    corr_val = round(valid_epc_data['Diff_EPC_SENSOR_POS'].corr(valid_epc_data['Diff_SHOULDER_LINE']), 3)

                    valid_epc_data.drop(['M_CELL_COUNT'],axis=1,inplace=True)
                    valid_epc_data = valid_epc_data.dropna().reset_index(drop=True)
                    
                    valid_epc_data['Window_Size'] = best_params[0]
                    valid_epc_data['Shift_Size'] = best_params[1]
                    valid_epc_data['LOT_ID'] = lot_id
                    valid_epc_data['Correlation_Value'] = corr_val
                    
                    utility.log_write(f"EPC - SHOULDER 상관계수 : {corr_val}")
                    
                    total_valid_list.append(valid_epc_data)
                
            if len(total_valid_list) > 0:
                utility.log_write(f'{len(total_valid_list)}개 Lot_ID 의 CTP-CTQ 상관분석 결과가 분석되었습니다.')
                total_valid_df = pd.concat(total_valid_list).reset_index(drop=True)
            
                total_valid_df.to_csv(self.corr_file_path, index=False)
            else:
                utility.log_write('CTP-CTQ 상관분석 결과가 존재하지 않습니다.')
                
            utility.log_write('CTP-CTQ 상관분석 작업 종료')
            
        except Exception as ex:
            utility.log_write(f"CTP-CTQ Correlation Analysis Error : {ex}")
            
            
            
    def get_shulder_line(self):
        # Cutting Height
        if self.shoulder_line == "TCH":
            self.vision_df['TOP_SHOULDER_LINE'] = self.vision_df['TOP_FRONT_CUTTING_HEIGHT']
            self.vision_df['BACK_SHOULDER_LINE'] = self.vision_df['TOP_BACK_CUTTING_HEIGHT']
            self.vision_df['SHOULDER_LINE'] = round(self.vision_df[['TOP_FRONT_CUTTING_HEIGHT','TOP_BACK_CUTTING_HEIGHT']].mean(axis=1), 3)

        # shoulder line
        elif self.shoulder_line == "TN":
            self.vision_df['TOP_SHOULDER_LINE'] = self.vision_df['TOP_COATING']
            self.vision_df['BACK_SHOULDER_LINE'] = self.vision_df['BOTTOM_COATING']
            self.vision_df['SHOULDER_LINE'] = round(self.vision_df[['TOP_COATING','BOTTOM_COATING']].mean(axis=1), 3)



    @staticmethod
    def find_mode_in_2d_list(two_d_list):
        if not two_d_list:
            return None  # 빈 리스트인 경우 None 반환
        
        # 리스트의 각 원소(리스트)를 튜플로 변환
        tuple_list = [tuple(sublist) for sublist in two_d_list]
        
        # 튜플 리스트에 대해 최빈값 찾기
        counter = Counter(tuple_list)
        mode_data = counter.most_common(1)  # 최빈값 찾기
        mode = mode_data[0][0]  # 튜플 형태의 최빈값
        return list(mode)  # 리스트 형태로 반환

    @staticmethod
    def NG_count(df):
        usl = header.SPEC_TCH_USL
        lsl = header.SPEC_TCH_LSL
        
        top_ng = list(df.loc[(df['TOP_SHOULDER_LINE'] >= usl) | (df['TOP_SHOULDER_LINE'] <= lsl)].index)
        b_ng = list(df.loc[(df['BACK_SHOULDER_LINE'] >= usl) | (df['BACK_SHOULDER_LINE'] <= lsl)].index)

        ng_count = len(set(top_ng+b_ng))
        
        return ng_count

    @staticmethod
    def simulation(simdata, cycle, gain, epc_vision_dist=75):
        usl = header.SPEC_TCH_USL
        lsl = header.SPEC_TCH_LSL
        ref = header.SPEC_TCH_REF
        
        offset_limit = header.OFFSET_TCH_LIMIT
        tolerance =header.GATHER_TOL_EPC # (lsl - tolerance) ~ (usl + tolerance)

        data_num = len(simdata)
        ii = 0
        
        while True:
        
            strj_CH_top = np.array([[]])
            strj_CH_back = np.array([[]])
        
            while (ii < data_num):
                
                val_CH_top = simdata.iloc[ii:ii+1, 0].values[0]
                val_CH_back = simdata.iloc[ii:ii+1, 1].values[0]
                ii = ii+1
                
                if val_CH_top > (lsl-tolerance) and val_CH_top < (usl+tolerance) and \
                    val_CH_back > (lsl-tolerance) and val_CH_back < (usl+tolerance) :
                
                    strj_CH_top = np.append(strj_CH_top, val_CH_top)
                    strj_CH_back = np.append(strj_CH_back, val_CH_back)
        
                else:
                    continue
                
                if strj_CH_top.size >= cycle:
                    break
            
            err = ref - (np.mean(strj_CH_top) + np.mean(strj_CH_back))/2
            offset = err * gain
            
            if offset > offset_limit:
                offset = offset_limit
            elif offset < -offset_limit:
                offset = -offset_limit
        
            idx2 = -(data_num - (ii + epc_vision_dist))
            
            
            if idx2 < 0:
                simdata.iloc[idx2:, [0,1]] = simdata.iloc[idx2:, [0,1]] + offset
            else:
                return simdata



    def set_change_flag(self, target_col, threshold=0.03, term_idx=200):
        # 초기 기준값과 새 컬럼 초기화
        self.result_df[f'{target_col}_Flag'] = 0  # 모든 행에 대해 초기 플래그 값은 0
        
        initial_ref = self.result_df.loc[0, target_col]
        self.result_df.loc[0, f'{target_col}_Flag'] = 1
        
        # 조건 검사 및 플래그 설정
        current_ref = initial_ref  # 현재 기준값
        last_reset_index = 0  # 마지막으로 기준점이 재설정된 인덱스

        for index, row in self.result_df.iterrows():
            if (len(self.result_df) - index) < 300:
                break
            if abs(row[target_col] - current_ref) >= threshold:
                self.result_df.loc[index, f'{target_col}_Flag'] = 1
                current_ref = row[target_col]  # 기준점 업데이트
                last_reset_index = index  # 기준점 업데이트 인덱스 저장

            if (index - last_reset_index) > term_idx:  # 인덱스가 200을 초과하는 경우
                current_ref = row[target_col]  # 새로운 기준점 설정
                last_reset_index = index  # 마지막 기준점 업데이트 인덱스 갱신


    def grid_search(self, window_sizes, shift_sizes):
        if self.shoulder_line =="TN":
            max_corr = float('-inf')
        elif self.shoulder_line=="TCH":
            max_corr = float('inf')
        best_params = None
        
        # Iterate over all combinations of window_sizes and shift_sizes
        for window in window_sizes:
            for shift in shift_sizes:
                # Calculate correlation for each combination
                corr = self.calculate_correlation(window, shift)
                # Update the best parameters if current correlation is higher
                if (self.shoulder_line =="TN") & (corr > max_corr):
                    max_corr = corr
                    best_params = (window, shift)
                elif (self.shoulder_line =="TCH") & (corr < max_corr):
                    max_corr = corr
                    best_params = (window, shift)
        return best_params, max_corr



    def calculate_correlation(self, window_size, shift_size):
        self.result_df['ROLLING_SHOULDER_LINE'] = self.result_df['SHOULDER_LINE'].rolling(window_size, center=True).median().shift(shift_size)  
        self.result_df = self.result_df.ffill().bfill()
        
        valid_epc_data = self.result_df.loc[self.result_df['EPC_SENSOR_POS_Flag']==1].reset_index(drop=True)
        
        valid_epc_data['Diff_EPC_SENSOR_POS'] = valid_epc_data['EPC_SENSOR_POS'].diff(1)
        valid_epc_data['Diff_SHOULDER_LINE'] = valid_epc_data['ROLLING_SHOULDER_LINE'].diff(1)

        correlation = round(valid_epc_data['Diff_EPC_SENSOR_POS'].corr(valid_epc_data['Diff_SHOULDER_LINE']), 3)
        return correlation
    
    
    def read_corr_file(self):
        corr_file_path = os.path.join(self.corr_dir_name, '*.csv')
        corr_file_list = glob(corr_file_path)[-5:]
        
        corr_map = map(self.read_file, corr_file_list)
        corr_df = pd.concat(corr_map, ignore_index=True)
        new_corr_df = corr_df[abs(corr_df['Correlation_Value'])> 0.7]
        return new_corr_df
    
        
    def train_model(self, X, y):
        # 1. 데이터 분할
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.1, random_state=42)
        
        # 2. 모델 학습
        self.model = LinearRegression()
        self.model.fit(X_train, y_train)

        # 4. 모델 검증
        y_pred = self.model.predict(X_test)
        mse = round(mean_squared_error(y_test, y_pred), 3)
        r2 = round(r2_score(y_test, y_pred)* 100, 2) 

        utility.log_write(f"Mean Squared Error: {mse}")
        utility.log_write(f"R-squared: {r2}%")
        
    
    def predict(self, target_y):
        # 모델의 절편과 기울기
        intercept = self.model.intercept_
        coefficient = self.model.coef_[0]
        x_value = round((target_y - intercept) / coefficient, 3)
        return x_value

