from datetime import date, timedelta
from typing import Literal
import json
import math


key_ss = "SS"
key_sf = "SF"
key_fs = "FS"
key_ff = "FF"

idx_deping = 0
idx_depded = 1
idx_deptyp = 2

id_digit_default = 4


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







class Gantt:
    def __init__(self, name:str):
        self.name = name
        self.tasks = []
        self.counter_dict: dict[str, int]= {'G':-1,
                                             'T':-1,
                                             'M':-1,
                                             'Q':-1,
                                             'C':-1,
                                            }
        self.dep_start:list[tuple[str, str, str]] = []  
        self.dep_fin = [tuple[str, str, str]] = []



    def add_task(self,
                 name:str,
                 cat_id:str|Literal['G','T', 'M', 'Q', 'C']|None,
                 num_id:int|None,
                 owner:str|list[str]|None,
                 date_start:str|date|None,
                 date_end:str|date|None,
                 num_duration:int|None,
                 unit_duration: Literal['day','week','month','year','wkg_day']|None,
                 name_dep_start:str|None,
                 typ_dep_start:Literal['SS','SF','FS','FF']|None,
                 name_dep_fin:str|None,
                 typ_dep_fin:Literal['SS','SF','FS','FF']|None,
                 ):
        if not name:
            raise ValueError("Task name cannot be empty.")
        
        if not cat_id:
            raise ValueError("Task category ID cannot be empty.")
        elif cat_id not in self.counter_dict:
            raise ValueError(f"Invalid task category ID: {cat_id}")
        if num_id is None:
            self.counter_dict[cat_id] += 1
            num_id = self.counter_dict[cat_id]

        if not owner:
            raise ValueError("Task owner cannot be empty.")
        elif isinstance(owner, str):
            task = Task(name=name,
                        cat_id=cat_id,
                        num_id=num_id,
                        owner=owner,
                        date_start=date_start,
                        date_end=date_end,
                        num_duration=num_duration,
                        unit_duration=unit_duration)
            self.tasks.append(task)
        else:
            for o in owner:
                task = Task(name=name,
                            cat_id=cat_id,
                            num_id=num_id,
                            owner=o,
                            date_start=date_start,
                            date_end=date_end,
                            num_duration=num_duration,
                            unit_duration=unit_duration)
                self.tasks.append(task)

        if name_dep_start is not None:
            if typ_dep_start is None:
                raise ValueError("Dependency type for start cannot be empty when start dependency name is provided.")
            else:
                tuple_dep_start = (name, name_dep_start, typ_dep_start)
                self.dep_start.append(tuple_dep_start)

        if name_dep_fin is not None:
            if typ_dep_fin is None:
                raise ValueError("Dependency type for finish cannot be empty when finish dependency name is provided.")
            else:
                tuple_dep_fin = (name, name_dep_fin, typ_dep_fin)
                self.dep_fin.append(tuple_dep_fin)



    def link(self):
        max = -1
        for cat in self.counter_dict:
            if self.counter_dict[cat] > max:
                max = self.counter_dict[cat]
        id_digit = math.floor(math.log10(max))+1
        if id_digit < id_digit_default:
            id_digit = id_digit_default

        for task in self.tasks:
            task.id = f"{task.cat_id}{task.num_id:0{id_digit}d}"



    