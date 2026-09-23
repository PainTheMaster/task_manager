from pathlib import Path
from typing import Any, Literal
import pandas as pd
import json
import plotly.graph_objects as go
import plotly.express as px



key_tasks = 'tasks'

key_task_name = "name"
key_task_id = "id"
key_task_owner = "owner"
key_date_start_calc = "date_start_calcd"
key_date_fin_calc = "date_fin_calcd"
key_caldays_needed = "calendar_days_needed"

key_name_dep_start = "name_dependency_start"
key_id_dep_start = "id_dependency_start"
key_typ_start = "typ_start"
key_lag_start = "lag_start"
key_name_dep_fin = "name_dependency_fin"
key_id_dep_fin = "id_dependency_fin"
key_typ_fin = "typ_fin"
key_preempt_fin = "preempt_fin"
key_description = "description"
key_flag_delay = "flag_delay"
key_color = 'color'
key_is_sub = "is_sub"

#derived
key_task_label = "task_label"

#for control
key_source_order = "_source_order"
key_owner_rank = '_owner_rank'
key_task_y = '_task_y'

key_color_delay = 'Delayed'


#dep type
key_ss = "SS"   #The task starts when the depending task starts
key_sf = "SF"   #The task finishes when the depending task starts
key_fs = "FS"   #The task starts when the depending task finishes
key_ff = "FF"   #The task finishes when the depending task finishes


def load_gantt_json(json_path: str|Path)->dict[str, Any]:
    """Load the input JSON file"""
    path = Path(json_path)
    with path.open('r', encoding='utf-8') as file:
        data = json.load(file)
    if key_tasks not in data:
        raise ValueError('"tasks" not in the JSON file.')
    if not isinstance(data[key_tasks], list):
        raise TypeError('"tasks" has to be an array.')
    return data


def prepare_dataframe(data: dict[str, Any]) -> pd.DataFrame:
    df = pd.DataFrame(data[key_tasks])
    required_columns = [
        key_task_id, key_task_name, key_task_owner, key_date_start_calc, key_date_fin_calc
    ]
    missing_columns = [c for c in required_columns if c not in df.columns]
    if missing_columns:
        raise ValueError("Missing mandatory items: "+",".join(missing_columns))

    df[key_date_start_calc] = pd.to_datetime(df[key_date_start_calc], format=r"%Y-%m-%d", errors="raise")

    df[key_date_fin_calc] = pd.to_datetime(df[key_date_fin_calc], format=r"%Y-%m-%d", errors="raise")

    invalid_dates=df[key_date_fin_calc] < df[key_date_start_calc]
    if invalid_dates.any():
        invalid_ids = df.loc[invalid_dates, key_task_id].tolist()
        raise ValueError('The following tasks have invalid datings: '+ ','.join(map(str,invalid_ids)))

    optional_defalults = {
        key_name_dep_start:None,
        key_id_dep_start:None,
        key_typ_start:None,
        key_lag_start:0,
        key_name_dep_fin:None,
        key_id_dep_fin:None,
        key_typ_fin:None,
        key_preempt_fin:0,
        key_description:None,
        key_flag_delay:False,
        key_is_sub: False,
        key_caldays_needed:None
    }

    for column, default_value in optional_defalults.items():
        if column not in df.columns:
            df[column] = default_value

    df[key_lag_start] = pd.to_numeric(df[key_lag_start], errors='coerce').fillna(0).astype(int)
    df[key_preempt_fin] = pd.to_numeric(df[key_preempt_fin], errors='coerce').fillna(0).astype(int)
    df[key_task_owner] = df[key_task_owner].fillna('No owner set').astype(str)
    df[key_task_label] = df[key_task_id].astype(str)+' '+df[key_task_name].astype(str)

    df[key_flag_delay] = df[key_flag_delay].fillna(False).astype(bool)
    df[key_color] = df[key_task_owner]
    df.loc[df[key_flag_delay]==True, key_color] = key_color_delay


    #dupulication dropped means the initial order of the owners is used as the rank of owners hereafter
    df[key_source_order] = range(len(df))
    owner_order = df[key_task_owner].drop_duplicates().tolist()
    owner_rank = {owner: i for i, owner in enumerate(owner_order)}
    df[key_owner_rank] = df[key_task_owner].map(owner_rank)
    df = df.sort_values([key_owner_rank, key_source_order], kind='stable').reset_index(drop=True)

    #Setting Y axis for each task (and organization)
    lane_gap = 0.9
    current_y = 0.0
    task_y: list[float] = []
    previous_owner: str|None = None
    for owner in df[key_task_owner]:
        if previous_owner is not None and owner != previous_owner:
            current_y += lane_gap
        task_y.append(current_y)
        current_y += 1.0
        previous_owner = owner
    df[key_task_y] = task_y

    return df

def add_swimlanes(
        fig: go.Figure,
        df: pd.DataFrame,
        date_freq: Literal['MS', '14D', '7D'] = 'MS',
        date_format:str=r'%Y-%m-%d'
) -> None:
    """
    Prepares a swim lane for each action owner.

    Action:
    1. Sets up a background band for each organization.
    2. Draws a border line at the bottom of each swim lane.
    3. Puts the organization name on the left.
    4. Puts a date scale at the bottom of each swim lane.

    Parameter
    ---------------
    fig:
        Plotly figure to be built.
        
    df:
        A DataFrame object generated by prepare_dataframe().
        This method requires columns corresponding to tag_task_owner, tag_task_y, tag_date_start, tag_date_fin.
    
    date_freq:
        Interval for date label.
        "MS": every first day of the month.
        "14D": 14-day interval.
        "7D": 7-day interval.

    date_format:
        Date format. The default is yyyy-mm-dd.
    """

    lane_colors = [
        "rgba(68, 114, 196, 0.055)",
        "rgba(112, 173, 71, 0.055)"
    ]

    #Prepares a common date scale.
    date_min = df[key_date_start_calc].min().normalize()
    date_max = df[key_date_fin_calc].max().normalize()

    tick_dates = pd.date_range(start=date_min,
                               end=date_max,
                               freq=date_freq)

    #If the starting day is not included in the tick_dates, the starting date of the project is added.
    if date_min not in tick_dates:
        tick_dates = tick_dates.insert(0, date_min)

    for lane_nr, (owner, group) in enumerate(df.groupby(key_task_owner, sort=False)):
        y0 = float(group[key_task_y].min())-0.45
        y1 = float(group[key_task_y].max())+0.45
        center = (y0 + y1) / 2

        #background band for each organization (task owner)
        fig.add_hrect(
            y0=y0,
            y1=y1,
            fillcolor=lane_colors[
                lane_nr % len(lane_colors)
            ],
            line_width=0,
            layer='below'
        )

        #Bottom border line for each swim lane.
        fig.add_hline(
            y=y1,
            line_width = 1,
            line_color="rgba(90, 90, 90, 0.35)",
            layer="below"
        )


        #Organization name
        fig.add_annotation(
            x=-0.20,
            y=center,
            xref='paper',
            yref='y',
            text=f'<b>{owner}</b>',
            showarrow=False,
            xanchor="right",
            yanchor="middle",
            align="right",
            font={"size":12,
                  "color": "#303030"}
        )

        for tick_date in tick_dates:
            #adding dates for each swim lane
            fig.add_annotation(
                x=tick_date,
                y=y1,
                xref="x",
                yref="y",
                text=tick_date.strftime(date_format),
                showarrow=False,
                xanchor='center',
                yanchor='top',
                yshift=-3,
                font={
                    "size":8,
                    "color":"#707070"
                },
                bgcolor="rgba(255,255,255,0.78)",
                borderpad=1
            )

            #adding short scale symbol lines at the dates
            fig.add_shape(
                type='line',
                x0=tick_date,
                x1=tick_date,
                y0=y1-0.06,
                y1=y1+0.06,
                xref="x",
                yref='y',
                line={
                    'color':'rgba(90,90,90,0.55)',
                    'width':1
                },
                layer='above',
            )




def add_lag_periods(
        fig: go.Figure,
        df: pd.DataFrame
)->None:
    task_by_id = {}
    for _, task in df.iterrows():
        if not task[key_is_sub]:
            task_by_id[str(task[key_task_id])]=task

    for _, this in df.iterrows():
        precessor_id = this[key_id_dep_start]
        lag_days = int(this[key_lag_start])
        if (pd.isna(precessor_id)
        or lag_days <= 0
        or str(precessor_id) not in task_by_id
        ):
            continue

        predeceessor = task_by_id[str(precessor_id)]
        relation = this[key_typ_start]

        if relation == key_fs:
            blank_start, blank_end = predeceessor[key_date_fin_calc],  this[key_date_start_calc]
        elif relation == key_ss:
            blank_start, blank_end = predeceessor[key_date_start_calc], this[key_date_start_calc]
        else:
            continue

        if blank_end <= blank_start:
            continue

        fig.add_trace(
            go.Bar(
                name='Lag',
                x=[(blank_end-blank_start).total_seconds()*1000],
                base=[blank_start],
                y=[float(this[key_task_y])],
                orientation='h',
                width=0.55,
                marker={
                    "color":"rgba(160,160,160,0.28)",
                    "line":{"color":"#8C8C8C", "width":1},
                    "pattern":{"shape":"/"},
                },
                customdata=[[predeceessor[key_task_id], this[key_task_id], lag_days]],
                hovertemplate=(
                    "<b>Lag period</b><br>"
                    "Predecessor: %{customdata[0]}<br>"
                    "Successor: %{customdata[1]}<br>"
                    "Lag: %{customdata[2]} days"
                    "<extra></extra>"
                ),
                showlegend=False
            )
        )


def add_preempt_periods(
        fig: go.Figure,
        df: pd.DataFrame
)->None:
    task_by_id = {}
    for _, task in df.iterrows():
        if not task[key_is_sub]:
            task_by_id[str(task[key_task_id])]=task

    for _, this in df.iterrows():
        successor_id = this[key_id_dep_fin]
        preempt_days = int(this[key_preempt_fin])
        if (pd.isna(successor_id)
        or preempt_days <= 0
        or str(successor_id) not in task_by_id
        ):
            continue

        successor = task_by_id[str(successor_id)]
        relation = this[key_typ_fin]

        if relation == key_sf:
            blank_start, blank_end = this[key_date_fin_calc],  successor[key_date_start_calc]
        elif relation == key_ff:
            blank_start, blank_end = this[key_date_fin_calc], successor[key_date_fin_calc]
        else:
            continue

        if blank_end <= blank_start:
            continue

        fig.add_trace(
            go.Bar(
                name='Lag',
                x=[(blank_end-blank_start).total_seconds()*1000],
                base=[blank_start],
                y=[float(this[key_task_y])],
                orientation='h',
                width=0.55,
                marker={
                    "color":"rgba(160,160,160,0.28)",
                    "line":{"color":"#8C8C8C", "width":1},
                    "pattern":{"shape":"/"},
                },
                customdata=[[this[key_task_id], successor[key_task_id], preempt_days]],
                hovertemplate=(
                    "<b>Preemption period</b><br>"
                    "Predecessor: %{customdata[0]}<br>"
                    "Successor: %{customdata[1]}<br>"
                    "Preemption: %{customdata[2]} days"
                    "<extra></extra>"
                ),
                showlegend=False
            )
        )

def get_dependency_points(
        this: pd.Series,
        depended: pd.Series,
        relation: str|None
)->tuple[pd.Timestamp, pd.Timestamp]:

    if not pd.isna(this[key_lag_start]):
        lag_days = pd.Timedelta(days=int(this[key_lag_start]))
    else:
        lag_days = pd.Timedelta(days=0)

    if not pd.isna(this[key_preempt_fin]):
        preempt_days = pd.Timedelta(days=int(this[key_preempt_fin]))
    else:
        preempt_days = pd.Timedelta(days=0)
    
    if relation == key_fs:
        return depended[key_date_fin_calc], this[key_date_start_calc]-lag_days
    elif relation == key_ss:
        return depended[key_date_start_calc], this[key_date_start_calc]-lag_days
    elif relation == key_sf:
        return depended[key_date_start_calc], this[key_date_fin_calc]+preempt_days
    elif relation==key_ff:
        return depended[key_date_fin_calc], this[key_date_fin_calc]+preempt_days
    else:
        raise ValueError(f'Undefined dependency type "{relation}".')
    


def add_dependency_arrows(
        fig: go.Figure,
        df: pd.DataFrame
):
    """
    Displays dependencies (start/finish) of the tasks.
    <ul>
    <li>Relationship between the tasks with an arrow.</li>
    <li>The end of an arrow on the left side of a task bar for starting.</li>
    <li>The end of an finishin arrow on the right side of a tas bar for finishin.</li>
    <li>Dependency type and blank length in case of lag or preemption.</li>
    </ul>
    """

    task_by_id = {}
    for _, task in df.iterrows():
        if not task[key_is_sub]:
            task_by_id[str(task[key_task_id])]=task

    for _, this in df.iterrows():
        dep_start_id = this[key_id_dep_start]
        dep_fin_id = this[key_id_dep_fin]

        #Firstly, starting dependecy.
        if not pd.isna(dep_start_id):
            dep_start_id = str(dep_start_id)
            
            if dep_start_id not in task_by_id:
                print(
                    'Depended task for starting not found.'
                    f'Depending task to start: "{this[key_task_id]}"'
                    f'Depended task: "{dep_start_id}"'
                )

            else:
                depended = task_by_id[dep_start_id]
                relation = str(this[key_typ_start])

                x_start, x_end = get_dependency_points(this = this,
                                                    depended=depended,
                                                    relation=relation)
                y_depended = float(depended[key_task_y])
                y_this = float(this[key_task_y])

                annotation_text = relation

                lag_days = int(this[key_lag_start])
                if (relation == key_fs or relation==key_ss) and lag_days > 0:
                    annotation_text += f'+{lag_days}d'
                fig.add_annotation(
                    x=x_end,
                    y=y_this,
                    ax=x_start,
                    ay=y_depended,
                    xref='x',
                    yref='y',
                    axref='x',
                    ayref='y',

                    text='',

                    showarrow=True,
                    arrowhead=2,
                    arrowsize=1,
                    arrowwidth=1.5,
                    arrowcolor='#555555'
                )

                task_start: pd.Timestamp = this[key_date_start_calc]
                task_fin:pd.Timestamp = this[key_date_fin_calc]
                task_duration = task_fin - task_start
                # allocate the dependency label 3% inside the bar from the left. Minimum 0.15 day maximum 1 day inside.
                offset_days = min(
                    max(task_duration.total_seconds()/(60*60*24)*0.03,0.15),
                    1.0
                )
                label_x=task_start+pd.Timedelta(days=offset_days)
                fig.add_annotation(
                    x=label_x,
                    y=y_this,

                    xref = 'x',
                    yref = 'y',

                    text=annotation_text,
                    showarrow=False,
                    xanchor='left',
                    yanchor='middle',
                    align='left',

                    font={
                        'size':9,
                        'color':'#404040'
                    },

                    bgcolor='rgba(255,255,255,0.85)',
                    borderwidth=1,
                    borderpad=2
                )

        #Secondly, finishing dependency.
        if not pd.isna(dep_fin_id):
            dep_fin_id = str(dep_fin_id)

            if dep_fin_id not in task_by_id:
                print(
                    'Depended task for finishing not found.'
                    f'Depending task to finish: "{this[key_task_id]}"'
                    f'Depended task: "{dep_fin_id}"'
                )

            else:
                depended = task_by_id[dep_fin_id]
                relation = str(this[key_typ_fin])

                x_start, x_end = get_dependency_points(this=this,
                                                       depended=depended,
                                                       relation=relation)
                y_depended = float(depended[key_task_y])
                y_this = float(this[key_task_y])

                annotation_text = relation

                preempt_days = int(this[key_preempt_fin])
                if(relation == key_sf or relation==key_ff) and preempt_days > 0:
                    annotation_text += f'+{preempt_days}d'
                fig.add_annotation(
                    x=x_end,
                    y=y_this,
                    ax=x_start,
                    ay=y_depended,
                    xref='x',
                    yref='y',
                    axref='x',
                    ayref='y',

                    text='',

                    showarrow=True,
                    arrowhead=2,
                    arrowsize=1,
                    arrowwidth=1.5,
                    arrowcolor='#555555'
                )

                task_start:pd.Timestamp = this[key_date_start_calc]
                task_fin:pd.Timestamp = this[key_date_fin_calc]
                task_duration = task_fin - task_start
                offset_days = min(
                    max(task_duration.total_seconds()/(60*60*24)*0.03, 0.15),
                    1.0
                )
                label_x = task_fin-pd.Timedelta(days=offset_days)
                fig.add_annotation(
                    x=label_x,
                    y=y_this,

                    xref = 'x',
                    yref = 'y',

                    text=annotation_text,
                    showarrow=False,
                    xanchor='right',
                    yanchor='middle',
                    align='right',

                    font={
                        'size':9,
                        'color':'#404040'
                    },

                    bgcolor='rgba(255,255,255,0.85)',
                    borderwidth=1,
                    borderpad=2
                )                



def make_gantt_chart(
        data: dict[str, Any],
        show_dependencies:bool=True,
        show_blank:bool=True
) -> go.Figure:
    """Makes an interactive swim lane type Gantt chart."""
    df = prepare_dataframe(data)
    project_name = data.get(key_task_name, 'Gantt chart')
    owner_colors ={
        "CSK":"#0000CD",
        "MSAT":"#4169E1",
        "製造":"#ED7D31",
        "QC":"#32CD32",
        "QA":"#2E8B57",
        "業務": "#00BFFF",
        key_color_delay: '#FF0000'
    }

    fig = px.timeline(
        data_frame=df,
        x_start=key_date_start_calc,
        x_end=key_date_fin_calc,
        y=key_task_y,
        color=key_color,
        text=key_task_name,
        color_discrete_map=owner_colors,
        custom_data=[key_task_id,   #0
                     key_task_name, #1
                     key_task_owner,    #2
                     key_caldays_needed,    #3
                     key_name_dep_start, #4
                     key_typ_start, #5
                     key_lag_start, #6
                     key_name_dep_fin,   #7
                     key_typ_fin,   #8
                     key_preempt_fin,   #9
                     key_description,   #10
                     key_flag_delay],   #11
        title=f'{project_name} Gantt Chart',
        labels={key_task_owner:'Organization'}
    )

    fig.update_traces(
        hovertemplate=(
            "<b>%{customdata[0]}: %{customdata[1]}</b><br>"
            "Organization: %{customdata[2]}<br>"
            "Start: %{base|%Y-%m-%d}<br>"
            "Calender days: %{customdata[3]}<br>"
            "Predecessor: %{customdata[4]}--%{customdata[5]}<br>"
            "Lag start: %{customdata[6]} days<br>"
            "Sucessor: %{customdata[7]}--%{customdata[8]}<br>"
            "Preempt fin: %{customdata[9]} days<br>"
            "Delay: %{customdata[11]}<br>"
            "%{customdata[10]}<br>"
            "<extra></extra>"
        ),
        marker_line_color = "white",
        marker_line_width = 1,
        opacity = 0.9,
        width = 0.62,
        textposition="outside",
        textfont={
            "size":10,
            "color":"black"
        }
    )

    add_swimlanes(fig, df)
    if show_blank:
        add_lag_periods(fig, df)
        add_preempt_periods(fig, df)
    if show_dependencies:
        add_dependency_arrows(fig, df)

    fig.update_yaxes(
        autorange='reversed',
        tickmode='array',
        tickvals=df[key_task_y].tolist(),
        ticktext=df[key_task_label].tolist(),
        title=None,
        showgrid=False,
        zeroline=False
    )

    owner_count = df[key_task_owner].nunique()
    fig.update_layout(
        template='plotly_white',
        height=max(640, 42*len(df)+52*owner_count+220),
        hovermode='closest',
        bargap=0.25,
        barmode='overlay',
        legend_title_text='Task Owner',
        margin={'l':350, 'r':60, 't':150, 'b':120},
        xaxis={
            'title':'Date',
            'side':'top',
            'tickformat':f'%Y-%m-%d',
            'showgrid':True,
            'gridcolor':'#E6E6E6',
            'rangeslider':{
                'visible':True,
                'thickness':0.08
            }
        }
    )

    return fig


def build_today_line_script(line_color:str="#D62728",
                            label:str='Today')->str:
    """
    Builds a JavaScript snippet for Plotly's post_script that draws a vertical line at today's date as seen by the browser that opens the HTML file.
    Because this runs client-side, the "today" it uses is always the date on which the viewer opens the page. recalculated every time the page loads.

    The '{plot_id}' placeholder is filled in by Poltly's 'write_html' with the id of the chart's div element.
    """

    return r"""
    (function() {
        var gd = document.getElementById('{plot_id}');
        if (!gd) {return;}

        var now = new Date();
        var y = now.getFullYear();
        var m = String(now.getMonth()+1).padStart(2, '0');
        var d = String(now.getDate()).padStart(2, '0');
        var todayStr = y + '-'+ m + '-' + d;

        var shapes = (gd.layout && gd.layout.shapes) ? gd.layout.shapes.slice() : [];
        shapes.push({
            type: 'line',
            xref: 'x',
            yref: 'paper',
            x0: todayStr,
            x1: todayStr,
            y0:0,
            y1:1,
            line:{color:'"""+line_color+r"""', width: 2, dash: 'dot'},
            layer:'above'
        });

        var annotations = (gd.layout && gd.layout.annotations) ? gd.layout.annotations.slice() : [];
        annotations.push({
            x: todayStr,
            y: 1,
            yref: 'paper',
            xref: 'x',
            text: '"""+label+r"""'+' '+todayStr,
            showarrow: false,
            xanchor: 'left',
            yanchor: 'bottom',
            font: {color: '""" + line_color + r"""', size: 10}
        });

        Plotly.relayout(gd, {shapes: shapes, annotations: annotations});
    
    })();
"""



def main()->None:
    input_json = Path("gantt.json")
    output_html = Path("gantt_swimlane.html")

    data = load_gantt_json(input_json)
    fig = make_gantt_chart(data=data, show_dependencies=True, show_blank=True)
    fig.write_html(
        file=output_html,
        include_plotlyjs=True,
        full_html=True,
        auto_open=False,
        post_script=[build_today_line_script()]
    )
    print('The Gantt chart is out put.')


if __name__ == '__main__':
    main()

