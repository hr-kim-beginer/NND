import time

class Ctimer:

    def __init__(self):
        self.__startTime = time.time()
        self.__elapsedTime = 0  # For Sec

    def reset(self):
        self.__startTime = time.time()
        self.__elapsedTime = 0

    def getstarttime(self):
        return self.__startTime

    def getElapsedTime(self):
        self.__elapsedTime = time.time() - self.__startTime
        return round(self.__elapsedTime, 0)

    def timer_condition(self, c):
        if bool(c) is False :
            self.reset()

    def set_time(self):
        self.reset()

    def tm_over(self, delay):
        self.__elapsedTime = time.time()-self.__startTime
        if self.__elapsedTime >= delay:
            return True
        return False

    def get_left_time(self, delay):
        self.__elapsedTime = time.time() - self.__startTime
        left_time = delay - self.__elapsedTime
        return round(left_time, 0)
    
def check_timer(func):
    timer_dict=dict()

    def create_timer(name):

        if name not in timer_dict:
            timer_dict[name]=Ctimer()

    def wrapper(*args, name='base', delay=0, **kwargs):
        create_timer(name=name)
        if timer_dict[name].tm_over(delay):
            result=func(*args,**kwargs)
            if delay!=0:
                timer_dict[name].reset()
            return result

    return wrapper
