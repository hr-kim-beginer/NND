import datetime
import header
import data_memory as dm
import numpy as np

class Data_set():
    def __init__(self, prefix_name):
        self.prefix_name = prefix_name

    def update(self, data_table):
        """_summary_
        : data_set 객체에 raw data, column명, index 할당
        
        Args:
            data_table (list): data, column명, index가 포함된 list
        """        
        if data_table is not None:
            self.raw_data = data_table[0]
            self.column_name = data_table[1]
            self.column_idx = data_table[2]


    def is_in_columns(self, columns_list):
        flag = True
        for i in columns_list:
            if i not in self.column_name:
                flag = False
                break
        return flag

    def last_data(self, columns_list=None):
        """ㅊㅇㅇ
        
        Parameters
        columns_list    : list

        Return
        np.array
        입력받은 column들의 가장 마지막 행 데이터

        """
        
        if columns_list is None:
            data = self.raw_data[-1]
        else:
            index = self.get_index_num(columns_list)
            data = self.raw_data[...,index][-1]
        return data

    def recent_time_data(self, columns_list=None, ntime=0):

        target_time = dm.system_time - datetime.timedelta(seconds=int(ntime))
        target_idx = self.raw_data[..., self.column_idx[header.I_TIME]] >= target_time

        if columns_list is None:
            data = self.raw_data[target_idx]
        else:
            index = self.get_index_num(columns_list)
            data = self.raw_data[...,index][target_idx]

        return data

    def recent_between_time_data(self, columns_list=None, st_time=0, end_time=0):

        if st_time == 0:
            st_target_time = dm.system_time - datetime.timedelta(days=1)
        else:
            st_target_time = dm.system_time - datetime.timedelta(seconds=st_time)
        end_target_time = dm.system_time - datetime.timedelta(seconds=end_time)

        st_target_idx = self.raw_data[..., self.column_idx[header.I_TIME]] >= st_target_time
        end_target_idx = self.raw_data[..., self.column_idx[header.I_TIME]] < end_target_time

        target_idx = np.logical_and(st_target_idx, end_target_idx)

        if columns_list is None:
            data = self.raw_data[target_idx]
        else:
            index = self.get_index_num(columns_list)
            data = self.raw_data[...,index][target_idx]
        return data

    def recent_row_data(self, columns_list=None, nrow=None):
        if columns_list is None:
            data = self.raw_data[:nrow]
        else:
            index = self.get_index_num(columns_list)
            data = self.raw_data[...,index][:nrow]

        return data

    def time_row_data(self, columns_list, st_time, end_time):

        st_target_idx = self.raw_data[..., self.column_idx[header.I_TIME]] >= st_time
        end_target_idx = self.raw_data[..., self.column_idx[header.I_TIME]] <= end_time

        target_idx = np.logical_and(st_target_idx, end_target_idx)

        if columns_list is None:
            data = self.raw_data[target_idx]
        else:
            index = self.get_index_num(columns_list)
            data = self.raw_data[...,index][target_idx]

        return data

    def get_index_num(self, columns_list):
        temp_list = []
        for i in columns_list:
            if i in self.column_idx.keys():
                temp_list.append(self.column_idx[i])
            else:
                return None
        if len(temp_list) > 0:
            return temp_list
        else:
            return None

    def get_data(self, columns_list=None):
        if columns_list is None:
            data = self.raw_data
        else:
            index = self.get_index_num(columns_list)
            data = self.raw_data[...,index]
        return data
