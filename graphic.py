from pathlib import Path
from typing import Any
import pandas as pd
import json
import plotly.graph_objects as go

tag_tasks = 'tasks'

tag_task_name = "name"
tag_task_id = "id"
tag_task_owner = "owner"
tag_date_start = "date_start_calcd"
tag_date_fin = "date_fin_calcd"

tag_dep_start = "name_dependency_start"
tag_typ_start = "typ_start"
tag_lag_start = "lag_start"
tag_dep_fin = "name_dependency_fin"
tag_typ_fin = "typ_fin"
tag_preempt_fin = "preempt_fin"
tag_description = "description"
tag_flag_delay = "flag_delay"

#derived
tag_task_label = "task_label"

#for control
tag_source_order = "_source_order"
tag_owner_rank = '_owner_rank'



def load_gantt_json(json_path: str|Path)->dict[str, Any]:
    """Load the input JSON file"""
    path = Path(json_path)
    with path.open('r', encoding='utf-8') as file:
        data = json.load(file)
    if tag_tasks not in data:
        raise ValueError('"tasks" not in the JSON file.')
    if not isinstance(data[tag_tasks], list):
        raise TypeError('"tasks" has to be an array.')
    return data


def prepare_dataframe(data: dict[str, Any]) -> pd.DataFrame:
    df = pd.DataFrame(data[tag_tasks])
    required_columns = [
        tag_task_id, tag_task_name, tag_task_owner, tag_date_start, tag_date_fin
    ]
    missing_columns = [c for c in required_columns if c not in df.columns]
    if missing_columns:
        raise ValueError("Missing mandatory items: "+",".join(missing_columns))

    df[tag_date_start] = pd.to_datetime(df[tag_date_start], format=r"%Y-%m-%d", errors="raise")

    invalid_dates=df[tag_date_fin] < df[tag_date_start]
    if invalid_dates.any():
        invalid_ids = df.loc[invalid_dates, tag_task_id].tolist()
        raise ValueError('The following tasks have invalid datings: '+ ','.join(map(str,invalid_ids)))

    optional_defalults = {
        tag_dep_start:None,
        tag_typ_start:None,
        tag_lag_start:0,
        tag_dep_fin:None,
        tag_typ_fin:None,
        tag_preempt_fin:0,
        tag_description:None,
        tag_flag_delay:False
    }

    for column, default_value in optional_defalults.item():
        if column not in df.columns:
            df[column] = default_value

    df[tag_lag_start] = pd.to_numeric(df[tag_lag_start], errors='coerce').fillna(0).astype(int)
    df[tag_preempt_fin] = pd.to_numeric(df[tag_preempt_fin], errors='coerce').fillna(0).astype(int)
    df[tag_task_owner] = df[tag_task_owner].fillna('No owner set').astype(str)
    df[tag_task_label] = df[tag_task_id].astype(str)+' '+df[tag_task_name].astype(str)

    #dupulication dropped means the initial order of the owners is used as the rank of owners hereafter
    df[tag_source_order] = range(len(df))
    owner_order = df[tag_task_owner].drop_duplicates().tolist()
    owner_rank = {owner: i for i, owner in enumerate(owner_order)}
    df[tag_owner_rank] = df[tag_task_owner].map(owner_rank)
    df = df.sort_values([tag_owner_rank, tag_source_order], kind='stable').reset_index(drop=True)
    



def make_gantt_chart(
        data: dict[str, Any],
        show_dependencies:bool=True,
        show_lag:bool=True
) -> go.Figure:
    """Makes an interactive swim lane type Gantt chart."""
    df = prepare_dataframe(data)



def main()->None:
    input_json = Path("gantt.json")
    output_htmp = Path("gantt_swimlane.html")

    data = load_gantt_json(input_json)

