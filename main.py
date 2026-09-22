from taskmanager import Gantt
import graphic


gantt = Gantt(name='gantt')

gantt.add_task(name=(plan:='Plan'),
               num_id=100,
               cat_id="G",
               owner='ぼく',
               date_start='2026-09-19',
               num_duration=1,
               unit_duration="month",
               description='しっかり考える')
gantt.add_task(name='Do',
               cat_id='G',
               num_id=100,
               owner='ぼく',
               name_dep_start=plan,
               typ_dep_start='FS',
               name_dep_fin=(check:='Check'),
               typ_dep_fin='SF',
               description='Just do it!')
gantt.add_task(name=check,
               cat_id='G',
               num_id=100,
               owner='ぼく',
               date_start='2026-10-26',
               num_duration=1,
               unit_duration='week',
               description='Check what you have done.')


gantt.add_task(name='Procurement',
               cat_id='T',
               owner='MSAT',
               date_start='2026-09-22',
               num_duration=1,
               unit_duration='month',
            #    typ_dep_fin='SF',
            #    name_dep_fin='Test',
               description='Procurement of the raw materials')

gantt.add_task(name='Testing',
               cat_id='Q',
               owner='MSAT',
               date_fin='2026-10-15',
               num_duration=1,
               unit_duration='month',
               typ_dep_start='FS',
               name_dep_start='Procurement',
               description='Acceptance test of the prcured RMs.')

gantt.link()

graphic.main()