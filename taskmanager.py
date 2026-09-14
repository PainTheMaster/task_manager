from datetime import date, timedelta
from typing import Literal
import json
import math


key_ss = "SS"   #The task starts when the depending task starts
key_sf = "SF"   #The task finishes when the depending task starts
key_fs = "FS"   #The task starts when the depending task finishes
key_ff = "FF"   #The task finishes when the depending task finishes

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
                 date_start:date|None,
                 date_fin:date|None,
                 num_duration:int|None,
                 unit_duration: Literal['day','week','month','year','wkg_day']|None,
                 dep_start:Task|None=None,
                 typ_dep_start:Literal['SS', 'FS']|None=None,
                 lag_start:int=0,
                 dep_fin:Task|None=None,
                 typ_dep_fin:Literal['SF','FF']|None=None,
                 preempt_fin:int=0,
                 description:str|None=None
                 ):
        if not name:
            raise ValueError("Task name cannot be empty.")
        else:
            self.name = name

        if not cat_id:
            raise ValueError("Task category ID cannot be empty.")
        else:
            self.cat_id = cat_id

        if not num_id:
            raise ValueError("Task number ID cannot be empty.")
        else:
            self.num_id = num_id

        self.id:str = None

        if not owner:
            raise ValueError("Task owner cannot be empty.")
        else:
            self.owner = owner

        self.date_start = date_start
        self.date_start_calcd:date = None
        self.date_fin = date_fin
        self.date_fin_calcd:date = None
        self.num_duration_need = num_duration
        self.unit_duration = unit_duration
        self.cal_days_needed:timedelta = None
        if self.num_duration_need and self.unit_duration:
            if self.unit_duration == 'day':
                self.cal_days_needed = timedelta(days=self.num_duration_need)
            elif self.unit_duration == 'week':
                self.cal_days_needed = timedelta(days=self.num_duration_need * 7)
            elif self.unit_duration == 'month':
                self.cal_days_needed = timedelta(days=self.num_duration_need * 30)
            elif self.unit_duration == 'year':
                self.cal_days_needed = timedelta(days=self.num_duration_need * 365)
            elif self.unit_duration == 'wkg_day':
                self.cal_days_needed = timedelta(days=(self.num_duration_need//5)*7 + self.num_duration_need%5)

        self.dep_start = dep_start
        if dep_start is None and typ_dep_start is None:
            self.dep_start = None
            self.typ_dep_start = None
        elif dep_start and not typ_dep_start:
            raise ValueError("Dependency type for start cannot be empty when start dependency name is provided.")
        elif dep_start is None and typ_dep_start:
            raise ValueError("Start dependency cannot be empty when dependency type is provided.")
        elif typ_dep_start != key_ss and typ_dep_start != key_fs:
            raise ValueError("Invalid dependency type for start. Must be 'SS' or 'FS'.")
        else:
            self.typ_dep_start = typ_dep_start

        self.lag_start = timedelta(days=lag_start)

        self.dep_fin = dep_fin
        if dep_fin is None and typ_dep_fin is None:
            self.dep_fin = None
            self.typ_dep_fin = None
        elif dep_fin and not typ_dep_fin:
            raise ValueError("Dependency type for finish cannot be empty when finish dependency name is provided.")
        elif dep_fin is None and typ_dep_fin:
            raise ValueError("Finish dependency cannot be empty when dependency type is provided.")
        elif typ_dep_fin != key_ff and typ_dep_fin != key_sf:
            raise ValueError("Invalid dependency type for finish. Must be 'FF' or 'SF'.")
        else:
            self.typ_dep_fin = typ_dep_fin

        self.preempt_fin = timedelta(days=preempt_fin)

        self.description = description
        self.is_start_determined = False
        self.is_fin_determined = False
        self.flag_delay = False


    def calc_dates(self) -> tuple[bool, bool]:
        prim_start:date = None
        prim_fin:date = None

        #start
        if self.date_start:
            prim_start = self.date_start
        if self.typ_dep_start == key_ss:
            if self.dep_start.date_start:
                temp_prim_start = self.dep_start.date_start + self.lag_start
                prim_start = temp_prim_start
                # if prim_start is None or temp_prim_start < prim_start:
                #     prim_start = temp_prim_start
            else:
                prim_start = None
        elif self.typ_dep_start == key_fs:
            if self.dep_start.date_fin:
                temp_prim_start = self.dep_start.date_fin + self.lag_start
                prim_start = temp_prim_start
                # if prim_start is None or temp_prim_start < prim_start:
                #     prim_start = temp_prim_start
            else:
                prim_start = None

        #end
        if self.date_fin:
            prim_fin = self.date_fin
        if self.typ_dep_fin == key_sf:
            if self.dep_fin.date_start:
                temp_prim_fin = self.dep_fin.date_start - self.preempt_fin
                if prim_fin is None or prim_fin < temp_prim_fin:    #次のタスクが始まるまで長く続けないといけない場合。
                    prim_fin = temp_prim_fin
            else:
                prim_fin = None
        if self.typ_dep_fin == key_ff:
            if self.dep_fin.date_fin:
                temp_prim_fin = self.dep_fin.date_fin - self.preempt_fin
                if prim_fin is None or prim_fin < temp_prim_fin:
                    prim_fin = temp_prim_fin
            else:
                prim_fin = None

        if self.cal_days_needed and prim_start:
            temp_prim_fin = prim_start + self.cal_days_needed
            if prim_fin is None or prim_fin < temp_prim_fin:
                prim_fin = temp_prim_fin

        changed:bool=False
        if self.date_start_calcd != prim_start or self.date_fin_calcd != prim_fin:
            changed = True

        self.date_start_calcd = prim_start
        self.date_fin_calcd = prim_fin

        
        if self.date_start_calcd is not None:
            self.is_start_determined = True
        else:
            self.is_start_determined = False
        if self.date_fin_calcd is not None:
            self.is_fin_determined = True
        else:
            self.is_fin_determined = False

        determined:bool = False
        if self.is_start_determined and self.is_fin_determined:
            determined = True
        else:
            determined = False

        #consistency check
        start_flag:bool = False
        fin_flag:bool = False
        if self.typ_dep_start == key_fs:
            if self.dep_start.date_fin and self.date_start:
                if self.date_start < self.dep_start.date_fin:
                    start_flag = True
                else:
                    start_flag = False
            else:
                start_flag = False
        elif self.typ_dep_start == key_ss:
            if self.dep_start.date_start and self.date_start:
                if self.date_start < self.dep_start.date_start:
                    start_flag = True
                else:
                    start_flag = False
            else:
                start_flag = False
        if self.date_fin and self.date_fin_calcd:
            if self.date_fin < self.date_fin_calcd:
                fin_flag = True
            else:
                fin_flag = False

        self.flag_delay = start_flag or fin_flag
        
        return (changed, determined)


    def task_to_dict(self):
        return {
            "name": self.name,
            "id": self.id,
            "owner": self.owner,
            "date_start_calcd":self.date_start_calcd.isoformat(),
            "date_fin_calcd":self.date_fin_calcd.isoformat(),
            "calender_days_needed": self.cal_days_needed.days,
            "name_dependency_start": self.dep_start.name,
            "id_dependency_start": self.dep_start.id,
            "typ_start": self.typ_dep_start,
            "lag_start": self.lag_start.days,
            "name_dependency_fin": self.dep_fin.name,
            "id_dependency_fin": self.dep_fin.id,
            "typ_fin": self.typ_dep_fin,
            "preempt_fin": self.preempt_fin.days,
            "description": self.description,
            "delay":self.flag_delay,
            
            "details":{
                "cat_id":self.cat_id,
                "num_id":self.num_id,
                "num_duration_needed":self.num_duration_need,
                "unit_duration":self.unit_duration,
                "start_determined": self.is_start_determined,
                "fin_determined": self.is_fin_determined,
            }
        }
            


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
                 date_fin:str|date|None,
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
                        date_fin=date_fin,
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
                            date_fin=date_fin,
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

        



    