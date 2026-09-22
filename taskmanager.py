from __future__ import annotations
from datetime import date, timedelta
from typing import Literal
from collections import namedtuple
import json
import math


key_ss = "SS"   #The task starts when the depending task starts
key_sf = "SF"   #The task finishes when the depending task starts
key_fs = "FS"   #The task starts when the depending task finishes
key_ff = "FF"   #The task finishes when the depending task finishes


id_digit_default = 4

dependency = namedtuple('dependency', ['name_this', 'name_dep', 'typ_dep'])


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
                 description:str|None=None,
                 is_sub:bool=False
                 ):
        if not name:
            raise ValueError("Task name cannot be empty.")
        else:
            self.name = name

        if not cat_id:
            raise ValueError("The category part of the task ID cannot be empty.")
        else:
            self.cat_id = cat_id

        if num_id is None:
            raise ValueError("The number part of the task ID cannot be empty.")
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

        self.lag_start = timedelta(days=lag_start if lag_start is not None else 0)

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

        self.preempt_fin = timedelta(days=preempt_fin if preempt_fin is not None else 0)

        self.description = description

        self.is_sub = is_sub
        self.circular_start_ok = False
        self.circular_fin_ok = False
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
            if self.dep_start.date_start_calcd:
                prim_start = self.dep_start.date_start_calcd + self.lag_start
                # if prim_start is None or temp_prim_start < prim_start:
                #     prim_start = temp_prim_start
            else:
                prim_start = None
        elif self.typ_dep_start == key_fs:
            if self.dep_start.date_fin_calcd:
                prim_start = self.dep_start.date_fin_calcd + self.lag_start
                # if prim_start is None or temp_prim_start < prim_start:
                #     prim_start = temp_prim_start
            else:
                prim_start = None
        # else:
        #     if self.date_start is None:
        #         raise RuntimeError(f'Task "{self.name}": The task has neither a dependency nor a starting date.')

        #end
        if self.date_fin:
            prim_fin = self.date_fin
        if self.typ_dep_fin == key_sf:
            if self.dep_fin.date_start_calcd:
                temp_prim_fin = self.dep_fin.date_start_calcd - self.preempt_fin
                if prim_fin is None or prim_fin < temp_prim_fin:    #次のタスクが始まるまで長く続けないといけない場合。
                    prim_fin = temp_prim_fin
            else:
                prim_fin = None
        elif self.typ_dep_fin == key_ff:
            if self.dep_fin.date_fin_calcd:
                temp_prim_fin = self.dep_fin.date_fin_calcd - self.preempt_fin
                if prim_fin is None or prim_fin < temp_prim_fin:
                    prim_fin = temp_prim_fin
            else:
                prim_fin = None
        # else:
        #     if self.date_fin is None:
        #         raise RuntimeError(f'Task "{self.name}": The task has neither a dependency nor a finishing date.')

        if self.cal_days_needed and prim_start:
            temp_prim_fin = prim_start + self.cal_days_needed
            if prim_fin is None or prim_fin < temp_prim_fin:
                prim_fin = temp_prim_fin

        if self.cal_days_needed and prim_fin:
            temp_prim_start = prim_fin - self.cal_days_needed
            if prim_start is None:
                prim_start = temp_prim_start

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

    def register_dependecy(self, dependency:Task, typ_dep:str):
        if typ_dep == key_ss or typ_dep == key_fs:
            self.dep_start = dependency
            self.typ_dep_start = typ_dep
        elif typ_dep == key_sf or typ_dep == key_ff:
            self.dep_fin = dependency
            self.typ_dep_fin = typ_dep


    def check_circular(self):
        if self.circular_start_ok and self.circular_fin_ok:
            return

        checked:list[Task] = [self]
        focus:Task = self
        while True:
            focus = focus.dep_start
            if focus is None:
                break
            checked.append(focus)
            if focus == self:
                circle = self.__list_linerize(checked)
                raise RuntimeWarning(f'Circular referencing in dependency series for starting:\n{circle}')
            else:
                focus.circular_start_ok = True
        focus = self
        while True:
            focus = focus.dep_fin
            if focus is None:
                break
            checked.append(focus)
            if focus == self:
                circle = self.__list_linerize(checked)
                raise RuntimeWarning(f'Circular referencing in dependency series for finishing:\n{circle}')
            else:
                focus.circula_fin_ok = True

    @staticmethod
    def __list_linerize(list_task:list[Task])->str:
        linearized:str=f'"{list_task[0].name}"'
        for i in range(1, len(list_task),1):
            linearized += f'->"{list_task[i].name}"'
        return linearized

    def task_to_dict(self):
        return {
            "name": self.name,
            "id": self.id,
            "owner": self.owner,
            "date_start_calcd":self.date_start_calcd.isoformat(),
            "date_fin_calcd":self.date_fin_calcd.isoformat(),
            "calendar_days_needed": self.cal_days_needed.days if self.cal_days_needed is not None else None,
            "name_dependency_start": self.dep_start.name if self.dep_start is not None else None,
            "id_dependency_start": self.dep_start.id if self.dep_start is not None else None,
            "typ_start": self.typ_dep_start,
            "lag_start": self.lag_start.days if self.lag_start is not None else None,
            "name_dependency_fin": self.dep_fin.name if self.dep_fin is not None else None,
            "id_dependency_fin": self.dep_fin.id if self.dep_fin is not None else None,
            "typ_fin": self.typ_dep_fin,
            "preempt_fin": self.preempt_fin.days if self.preempt_fin is not None else None,
            "description": self.description,
            "flag_delay":self.flag_delay,
            "is_sub": self.is_sub,

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
    #dependency = namedtuple('dependecy', ['name_this', 'name_dep', 'typ_dep'])

    def __init__(self, name:str):
        self.name = name
        self.tasks:list[Task] = []
        self.counter_dict: dict[str, int]= {'G':-1,
                                             'T':-1,
                                             'M':-1,
                                             'Q':-1,
                                             'C':-1,
                                            }

        #tuple_dep_fin = (name, name_dep_fin, typ_dep_fin)
        # self.dependency = namedtuple('dependecy', ['name_this', 'name_dep'])
        self.dep_start:list[dependency] = []  
        self.dep_fin: list[dependency] = []



    def add_task(self,
                 name:str=None,
                 cat_id:str|Literal['G','T', 'M', 'Q', 'C']=None,
                 num_id:int|None=None,
                 owner:str|list[str]=None,
                 date_start:str|date|None=None,
                 date_fin:str|date|None=None,
                 num_duration:int|None=None,
                 unit_duration: Literal['day','week','month','year','wkg_day']|None=None,
                 name_dep_start:str|None=None,
                 typ_dep_start:Literal['SS', 'FS']|None=None,
                 lag_start:int|None=None,
                 name_dep_fin:str|None=None,
                 typ_dep_fin:Literal['SF', 'FF']|None=None,
                 preempt_fin:int|None=None,
                 description:str|None=None
                 ):
        if not name:
            raise ValueError("Task name cannot be empty.")
        
        if not cat_id:
            raise ValueError(f'Task "{self.name}": Task category ID cannot be empty.')
        elif cat_id not in self.counter_dict:
            raise ValueError(f'Task "{self.name}": Invalid task category ID "{cat_id}"')
        if num_id is None:
            self.counter_dict[cat_id] += 1
            num_id = self.counter_dict[cat_id]

        if date_start is None:
            pass
        elif isinstance(date_start, str):
            date_start = date.fromisoformat(date_start)
        elif isinstance(date_start, date):
            pass
        else:
            raise ValueError(f'Task "{self.name}": invalid starting date input form "{date_start}"')

        if date_fin is None:
            pass
        elif isinstance(date_fin, str):
            date_fin = date.fromisoformat(date_fin)
        elif isinstance(date_fin, date):
            pass
        else:
            raise ValueError(f'Task "{self.name}": invalid finishing date input form "{date_fin}"')

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
                        unit_duration=unit_duration,
                        lag_start=lag_start,
                        preempt_fin=preempt_fin,
                        description=description,
                        is_sub=False
                        )
            self.tasks.append(task)
        else:
            isSub = False
            for o in owner:
                task = Task(name=name,
                            cat_id=cat_id,
                            num_id=num_id,
                            owner=o,
                            date_start=date_start,
                            date_fin=date_fin,
                            num_duration=num_duration,
                            unit_duration=unit_duration,
                            lag_start=lag_start,
                            preempt_fin=preempt_fin,
                            description=description,
                            is_sub=isSub)
                isSub = True
                self.tasks.append(task)

        if name_dep_start is not None:
            if typ_dep_start is None:
                raise ValueError("Dependency type for start cannot be empty when start dependency name is provided.")
            else:
                #tuple_dep_start = (name, name_dep_start, typ_dep_start)
                tuple_dep_start = dependency(name_this=name, name_dep=name_dep_start, typ_dep=typ_dep_start)
                self.dep_start.append(tuple_dep_start)

        if name_dep_fin is not None:
            if typ_dep_fin is None:
                raise ValueError("Dependency type for finish cannot be empty when finish dependency name is provided.")
            else:
                tuple_dep_fin = dependency(name_this=name, name_dep=name_dep_fin, typ_dep=typ_dep_fin)
                self.dep_fin.append(tuple_dep_fin)

    def find_by_name(self, name_dep:str)->Task:
        for task in self.tasks:
            if task.name == name_dep and not task.is_sub:
                return task
        return None


    # def check_circular(self, task_this:Task):
    #     list_checked:list[Task]=[task_this]
    #     if not task_this.circular_start_ok:
    #         pass
    #     pass

    def link(self):
        max = 1
        for cat in self.counter_dict:
            if self.counter_dict[cat] > max:
                max = self.counter_dict[cat]
        id_digit = math.floor(math.log10(max))+1
        if id_digit < id_digit_default:
            id_digit = id_digit_default
        for task in self.tasks:
            task.id = f"{task.cat_id}{task.num_id:0{id_digit}d}"

        for dep in self.dep_start:
            task_this = self.find_by_name(dep.name_this)
            task_dep = self.find_by_name(dep.name_dep)
            if task_dep is None:
                raise ValueError(f'Task name="{task_this.name}", ID="{task_this.id}": Dependency to start "{dep.name_dep}" not found.')
            task_this.register_dependecy(dependency=task_dep, typ_dep=dep.typ_dep)

        for dep in self.dep_fin:
            task_this = self.find_by_name(dep.name_this)
            task_dep = self.find_by_name(dep.name_dep)
            if task_dep is None:
                raise ValueError(f'Task name="{task_this.name}", ID="{task_this.id}": Dependency to finish "{dep.name_dep}" not found.')
            task_this.register_dependecy(dependency=task_dep, typ_dep=dep.typ_dep)

        for task in self.tasks:
            task.check_circular()

        changed = True
        determined = False
        while changed or not determined:
            changed = False
            determined = True
            for task in self.tasks:
                changed_this, deteremined_this = task.calc_dates()
                changed |= changed_this
                determined &= deteremined_this
            if not changed and not determined:
                raise RuntimeError('Not a deterministic plan.')

        tasks:list[dict]=[]
        for task in self.tasks:
            tasks.append(task.task_to_dict())
        
        dict_gantt = {'name':self.name,
                      'tasks': tasks}
        with open(file="gantt.json",mode='w',encoding='utf-8') as f:
            json.dump(obj=dict_gantt,
                      fp=f,
                      ensure_ascii=False)

    

    class CounterCategory:
        def __init__(self, cats: list[str]=None):
            self.used = {}
            for cat in cats:
                self.dict_cat[cat] = [(-1,-1)]
            


    
        



    