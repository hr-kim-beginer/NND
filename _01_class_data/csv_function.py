import os
import header
import utility
import numpy as np
import pandas as pd
import status_code
import shutil
import warnings
#remove futurewaring message
warnings.filterwarnings(action="ignore")


class MyCSV() :
    def __init__(self):
        self.equipment_state = None
        self.plc_last_dt = None         # PLC 데이터 마지막 읽은 시간
        self.vision_last_dt = None      # Vision 데이터 마지막 읽은 시간

        self.no_data = False
        self.vision_delay = False
        

    # csv 관련 parameter 관리
    def DB_table_name_to_csv_file_name(self, db_table_name):
        if db_table_name == header.TABLE_NAME_NOTCH_DATA :
            file_prefix = header.CSV_PLC_PREFIX
        elif db_table_name == header.TABLE_NAME_VISION_DATA :
            file_prefix = header.CSV_VISION_PREFIX
        else :
            file_prefix = None
        return file_prefix


    def find_file_path_list(self, db_table_name):

        self.prefix = self.DB_table_name_to_csv_file_name(db_table_name=db_table_name)

        full_fnames = []
        ref_fnames = []

        if db_table_name == header.TABLE_NAME_NOTCH_DATA :
            csv_file_path = header.CSV_FILE_PATH_PLC
        elif db_table_name == header.TABLE_NAME_VISION_DATA :
            csv_file_path = header.CSV_FILE_PATH_VISION


        for root, dirs, files in os.walk(csv_file_path):
            if 'BACKUP' in root:
                continue
            for fname in files:
                if self.prefix in fname :  #! startswith => contains
                    full_fname = os.path.join(root, fname)
                    full_fname = os.path.normpath(full_fname)
                    full_fnames.append(full_fname)
                    if fname.find('-') == -1 :
                        ref_fnames.append(full_fname)

        return ref_fnames, full_fnames
    
    
    def csv_read(self, file_name_path, all_path_list, table_name=None):  ### -1붙은 애들을 한꺼번에 부르기위한 함수
        try:
            fname_without_ext = file_name_path[:-4] ## '.csv' 지운 경로
            current_dataframe = pd.DataFrame()

            for i in range(len(all_path_list)):
                if all_path_list[i].startswith(fname_without_ext) :
                    
                    temp_csv = self.csv_safe_reader(all_path_list[i], table_name=table_name)
                    if temp_csv is not None :
                        ##pandas append 삭제로인한 concat 대체
                        current_dataframe = pd.concat([current_dataframe,temp_csv], sort=False,ignore_index=True)

                        # current_dataframe = current_dataframe.append(temp_csv, sort=False)
                    else :
                        current_dataframe = None
            if current_dataframe is not None :
                #lower -> upper
                # current_dataframe.columns = current_dataframe.columns.str.upper()
                current_dataframe.columns = current_dataframe.columns.str.strip()

            return(current_dataframe)
        
        except Exception as ex:
            message = f"{table_name} File_Read_Alarm"
            utility.log_write(f"{message} : {ex}")


    def csv_safe_reader(self, filename, table_name=None): ## PIE와의 충돌을 피하기 위해, 파일을 복사해서 사용한다.

        try :

            temp_filename = 'dont_touch/temp' + '_' + table_name + '.csv'
            shutil.copyfile(filename, dst=temp_filename)
            dataset = pd.read_csv(temp_filename, on_bad_lines='skip', encoding_errors='ignore') # 0929 파일럿 음극 vision error line 존재

        except Exception as ex :
            utility.log_write_by_level("csv_safe_reader 실패...{}".format(ex),level='critical')
            dataset = None

        return(dataset)

    
    def csv_select(self, table_name):
                    
        file_path_list, all_path_list = self.find_file_path_list(db_table_name=table_name)
        
        # 파일이 존재하지 않는 경우,
        if not file_path_list:
            message = f"{self.prefix} File Not Founded."
            utility.log_write(message, name='csv_function', delay=60)

            if self.prefix == 'PLC':
                utility.alarm_code_refresh(msg=message, err_code=status_code.PLC_File_Read_Alarm)
                
            #! 비전의 경우, 부동인 경우 파일이 존재하지 않아, 알람 울리지 않음.
            # else:
            #     utility.alarm_code_refresh(msg=message, err_code=status_code.Vision_File_Read_Alarm)
                
            return None
        
        last_file_path = file_path_list[-1]
        current_csv_file = self.csv_read(file_name_path=last_file_path, all_path_list=all_path_list, table_name=table_name)
        
        # 파일을 읽었는데 데이터가 존재하지 않는 경우,
        if len(current_csv_file) == 0:
            return None
        
        if self.prefix == 'PLC':
            time_col = header.I_TIME
            self.last_datetime = self.plc_last_dt 
            if header.SIMULATION_MODE:
                current_csv_file[time_col] = pd.to_datetime(current_csv_file[time_col], format='%Y-%m-%d %H:%M:%S.%f', errors='coerce')
            else:
                current_csv_file[time_col] = pd.to_datetime(current_csv_file[time_col], format='%Y%m%d%H%M%S%f', errors='coerce')
            
        elif self.prefix == 'Vision':
            time_col = header.I_VISION_INPUT_TIME
            self.last_datetime = self.vision_last_dt
            if header.SIMULATION_MODE:
                current_csv_file[time_col] = pd.to_datetime(current_csv_file[time_col], format='%Y-%m-%d %H:%M:%S.%f', errors='coerce')
            else:
                current_csv_file[time_col] = pd.to_datetime(current_csv_file[time_col], format='%Y%m%d%H%M%S%f', errors='coerce')
        
        # 마지막 읽은 시간 이후 데이터만 가져오기
        if self.last_datetime is not None:
            current_csv_file = current_csv_file[current_csv_file[time_col]>self.last_datetime]
        current_csv_file = current_csv_file.sort_values(by=[time_col], ascending=True).reset_index(drop=True)
        
        if self.prefix == 'Vision':
            # 시간 컬럼에 0값을 갖고 있는 행 제외
            time_zero_cnt = current_csv_file[time_col].isnull().sum()
            current_csv_file = current_csv_file.dropna(subset=[time_col]).reset_index(drop=True)
            if time_zero_cnt:
                message = f"{self.prefix} : The time data was invalid and has been removed."
                utility.write_log_alarm(message, err_code=status_code.Vision_Data_Invalid_Alarm)
                utility.log_write(message, name='csv_function', delay=60)
                
            # 데이터 값 중 -9999를 갖고 있는 행 제외
            outlier_cnt = sum(current_csv_file.isin([-9999]).any(axis=1))
            current_csv_file = current_csv_file[~current_csv_file.isin([-9999]).any(axis=1)].reset_index(drop=True)
            if outlier_cnt:
                message = f"{self.prefix} : The data with a value of -9999 has been removed."
                utility.alarm_code_refresh(msg=message, err_code=status_code.Vision_Data_Invalid_Alarm)
                utility.log_write(message, name='csv_function', delay=60)
            
        # 이상치 제거 후, 데이터 있는지 확인.
        if len(current_csv_file) == 0:
            return None
            
            
        # 데이터 단위 맞춰주기!
        if self.prefix == 'PLC':
            # 컬럼의 값들을 100으로 나누기
            for index in header.COLUMNS_TO_DIVIDE_100 :
                if index in current_csv_file:
                    current_csv_file[index] /= int(header.HUNDRED)
            # 컬럼의 값들을 1000으로 나누기
            for index in header.COLUMNS_TO_DIVIDE_1000 :
                            if index in current_csv_file:
                                current_csv_file[index] /= int(header.THOUSAND)
            # 마지막으로 읽은 시간 업데이트!!
            self.equipment_state = str(current_csv_file.loc[len(current_csv_file)-1, header.I_EQUIPMENT_STATE])  
            self.plc_last_dt = current_csv_file.loc[len(current_csv_file)-1, time_col]  

        elif self.prefix == 'Vision':
            # Vision 수집 지연 4초 초과인 경우, 데이터 제외.
            self.check_vision_delay(current_csv_file)
            # 마지막으로 읽은 시간 업데이트!!
            self.vision_last_dt = current_csv_file.loc[len(current_csv_file)-1, time_col] 
    
            
        colnames = current_csv_file.columns
        colname_to_idx = {colnames[i] : i for i in range(len(colnames))}
        current_csv_file = np.asarray(current_csv_file) #array 자료형 변환
        
        time_temp = current_csv_file[..., colname_to_idx[time_col]]
        time_temp2 = [element.to_pydatetime() for element in time_temp]
        current_csv_file[..., colname_to_idx[time_col]] = time_temp2.copy()

        return [current_csv_file, colnames, colname_to_idx]

    def data_ready(self): 
        """_summary_
        :CSV FILE READ
        
            Args:
                nrow (int, optional):목적에 따라 불러올 데이터의 Row 수를 다르게 하기 위함임 . Defaults to None.
        """        
        try :
            ## csv select 하면 시간에따라 순차적임!
            self.notch_data_total = self.csv_select(table_name=header.TABLE_NAME_NOTCH_DATA)   # a_notch_data
            self.vision_data_total = self.csv_select(table_name=header.TABLE_NAME_VISION_DATA) # a_vision
            
            # print(f"plc_last_dt : {self.plc_last_dt}\t vision_last_dt : {self.vision_last_dt}")

            #! 데이터 갯수 확인 
            if (self.notch_data_total == None):
                self.no_data = True
            else:
                self.no_data = False
                
        except Exception as ex :
            message = f"{self.prefix} File Read Error Occured"
            if self.prefix == 'PLC':
                utility.alarm_code_refresh(msg=message, err_code=status_code.PLC_File_Read_Alarm)
            else:
                utility.alarm_code_refresh(msg=message, err_code=status_code.Vision_File_Read_Alarm)
        
            utility.log_write(message, name='csv_function', delay=60)
            utility.log_write_by_level("CSV 데이터 수집 중 에러 발생 : {}".format(ex), level='critical', delay=10)


            self.notch_data_total = None
            self.vision_data_total = None


    def select_rows_from_csv_data(self, dataset, nrow):

        np_array = dataset[0]
        colnames = dataset[1]
        colnames_to_idx = dataset[2]

        return [np_array[:nrow], colnames, colnames_to_idx]


    def select_cols_from_dataframe(self, dataset, select_colnames): ## dataset은 csv_select의 리턴값 3묶음이 필요

        np_array = dataset[0]
        colnames = dataset[1]
        colnames_to_idx = dataset[2]

        if (type(select_colnames) is list) and (len(colnames) >= 2) :
            return np_array[..., [colnames_to_idx[colname] for colname in select_colnames]]
        else :
            return np_array[..., colnames_to_idx[select_colnames]]


    def get_file_size(self, files_path_list):
        files_size = [os.path.getsize(file) for file in files_path_list]
        return np.array(files_size)

    def get_time_name(self,files_path):
        files_time_name = [".".join(os.path.split(file_path)[-1].split('.')[1:]) for file_path in files_path]
        return files_time_name



    def check_vision_delay(self, data):
        check_delay_df = pd.DataFrame()
        check_delay_df['TIME'] = pd.to_datetime(data[header.I_VISION_TIME], format='%Y%m%d%H%M%S%f', errors='coerce')
        check_delay_df['VISION_OUTPUT_TIME'] = pd.to_datetime(data['VISION_OUTPUT_TIME'], format='%Y%m%d%H%M%S%f', errors='coerce')
        check_delay_df['Diff Time'] = check_delay_df['TIME'] - check_delay_df['VISION_OUTPUT_TIME'] 
        check_delay_df['Diff Time'] = check_delay_df['Diff Time'].apply(lambda x: x.total_seconds())

        check_delay_df = check_delay_df[check_delay_df['Diff Time']>int(header.GATHERING_DELAY_SEC)].reset_index(drop=True)
        delayed_vision_num = len(check_delay_df)
        

        if delayed_vision_num > 0:
            max_diff_time = round(max(check_delay_df['Diff Time']),3)
            message = f"Vision 데이터 수집 최대 {max_diff_time}초 지연이 {delayed_vision_num}건 발생하였습니다. \n {check_delay_df.loc[0,'VISION_OUTPUT_TIME']} <=> {check_delay_df.loc[0,'TIME']}"
            utility.alarm_code_refresh(msg="Vision_Data_Delayed_Alarm", err_code=status_code.Vision_Data_Delayed_Alarm)
            utility.log_write(message) 
            self.vision_delay = True
        else:
            self.vision_delay = False
        del check_delay_df