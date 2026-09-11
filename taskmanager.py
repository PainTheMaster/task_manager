from datetime import date, timedelta
from typing import Literal



class Task:
    def __init__(self,
                 name:str,
                 cat_id:str|Literal['G','T', 'M', 'Q', 'C']|None,
                 num_id:int|None,
                 owner:str|list[str]|None,
                 date_start:str|date|None,
                 date_end:str|date|None,
                 num_duration:int|None,
                 unit_duration: Literal['day','week','month','year','wkg_day']|None
                 ):
        self.name = name
        pass