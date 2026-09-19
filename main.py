from taskmanager import Gantt

gantt = Gantt(name='test')

gantt.add_task(name=(plan:='Plan'),
               cat_id="G",
               owner='ぼく',
               date_start='2026-09-19',
               num_duration=1,
               unit_duration="month",
               description='しっかり考える')
gantt.add_task(name='Do',
               cat_id='G',
               owner='ぼく',
               name_dep_start=plan,
               typ_dep_start='FS',
               name_dep_fin=(check:='Check'),
               typ_dep_fin='SF',
               description='Just do it!')
gantt.add_task(name=check,
               cat_id='G',
               owner='ぼく',
               date_start='2026-10-26',
               num_duration=1,
               unit_duration='week',
               description='Check what you have done.')

gantt.link()

