#!/usr/bin/env python2
import atexit
import math
import sys
import time
import numpy
import openravepy
import libcd

def multidot(*args):
   res = args[0]
   for m in args[1:]:
      res = numpy.dot(res,m)
   return res

def H_from_pose(pose):
   H = numpy.eye(4)
   libcd.kin.pose_to_H(pose,H,True)
   return H

M_SQRT1_2 = math.sqrt(0.5)

# hardcoded poses
pose_ee_palm = [ 0., 0., 0.1365, 0., 0., 0., 1. ]
pose_mug_grasp1 = [ 0.15, 0., 0.09, -0.5, -0.5, 0.5, 0.5 ]
pose_mugT = [ -0.3975, 1.61, 0.735, 0., 0., 1., 0. ] # table
pose_mugD = [ -1.1, 2.3, 0.0, 0.,0.,M_SQRT1_2,-M_SQRT1_2 ] # bin
pose_mug_drop = [ -1.1, 2.3, 0.735, 0.,0.,M_SQRT1_2,-M_SQRT1_2 ] # drop location

if len(sys.argv) != 2:
   print('Usage: {} <seed-int>'.format(sys.argv[0]))
   exit(1)

# create an environment, load the robot (wam)
openravepy.RaveInitialize(True, level=openravepy.DebugLevel.Info)
atexit.register(openravepy.RaveDestroy)
e = openravepy.Environment()
atexit.register(e.Destroy)

#e.SetViewer('qtcoin')

# add fixed objects (kitchen, table, bin)
kb_kitchen = e.ReadKinBodyXMLFile('environments/pr_kitchen.kinbody.xml')
if not kb_kitchen:
   raise RuntimeError('kitchen not found!')
e.Add(kb_kitchen)
kb_table = e.ReadKinBodyXMLFile('objects/furniture/table_zup.kinbody.xml')
if not kb_table:
   raise RuntimeError('table not found!')
e.Add(kb_table)
kb_table.SetTransform(H_from_pose([-0.3975,1.61,0., 0.,0.,-M_SQRT1_2,M_SQRT1_2]))
kb_bin = e.ReadKinBodyXMLFile('objects/household/recyclingbin-zlevel.kinbody.xml')
if not kb_bin:
   raise RuntimeError('recyclingbin not found!')
e.Add(kb_bin)
kb_bin.SetTransform(H_from_pose([-1.1,2.3,0.0, 0.,0.,-M_SQRT1_2,M_SQRT1_2]))
#kb_frame = e.ReadKinBodyXMLFile('objects/misc/coordframe.kinbody.xml')
#e.Add(kb_frame)
#kb_frame.Enable(False)
kb_mug = e.ReadKinBodyXMLFile('objects/household/mug2.kinbody.xml')
if not kb_mug:
   raise RuntimeError('mug not found!')
e.Add(kb_mug)

# load a robot, ik solver
r = e.ReadRobotXMLFile('robots/herb2_padded_nosensors.robot.xml')
e.Add(r)
r.SetTransform(H_from_pose([-0.3975,2.38,0., 0.,0.,-M_SQRT1_2,M_SQRT1_2]));
dofvals = [
   5.759, -1.972, -0.20, 1.9, 0., 0., 0., 1.3,1.3,1.3,0., # right
   0.630, -1.900,  0.15, 1.9, 0., 0., 0., 2.3,2.3,2.3,0.  # left
]
r.SetDOFValues(dofvals,range(len(dofvals)))
r.SetActiveManipulator("right_wam")
r.SetActiveDOFs(r.GetActiveManipulator().GetArmIndices())
ikmodel = openravepy.databases.inversekinematics.InverseKinematicsModel(r,
   iktype=openravepy.IkParameterization.Type.Transform6D)
if not ikmodel.load():
   ikmodel.autogenerate()

# get iks for mug on table
kb_mug.SetTransform(H_from_pose(pose_mugT))
H = numpy.dot(
   numpy.dot(kb_mug.GetTransform(), H_from_pose(pose_mug_grasp1)),
   numpy.linalg.inv(H_from_pose(pose_ee_palm))
   )
mugiksT = r.GetActiveManipulator().FindIKSolutions(H, openravepy.IkFilterOptions.CheckEnvCollisions)

# get iks for mug at drop location
kb_mug.SetTransform(H_from_pose(pose_mug_drop))
H = numpy.dot(
   numpy.dot(kb_mug.GetTransform(), H_from_pose(pose_mug_grasp1)),
   numpy.linalg.inv(H_from_pose(pose_ee_palm))
   )
mugiksdrop = r.GetActiveManipulator().FindIKSolutions(H, openravepy.IkFilterOptions.CheckEnvCollisions)


# create the three problem definitions (encoded as planner parameters xmls)

def s1():
   r.Release(kb_mug)
   kb_mug.SetTransform(H_from_pose(pose_mugT))
   #r.SetDOFValues([0.,0.,0.,0.],[7,8,9,10]) # open
p1 = openravepy.Planner.PlannerParameters()
p1.SetExtraParameters(''
   + '<startstate>5.759 -1.972 -0.20 1.9 0. 0. 0.</startstate>\n'
   + '\n'.join(['<goalstate>{}</goalstate>'.format(' '.join(str(v) for v in q)) for q in mugiksT])
)

def s2():
   r.Release(kb_mug)
   kb_mug.SetTransform(multidot(
      r.GetActiveManipulator().GetEndEffectorTransform(),
      H_from_pose(pose_ee_palm),
      numpy.linalg.inv(H_from_pose(pose_mug_grasp1))
      ))
   #r.SetDOFValues([1.5,1.5,1.5,0.],[7,8,9,10]) # closed
   r.Grab(kb_mug)
p2 = openravepy.Planner.PlannerParameters()
p2.SetExtraParameters(''
   + '\n'.join(['<startstate>{}</startstate>'.format(' '.join(str(v) for v in q)) for q in mugiksT])
   + '\n'.join(['<goalstate>{}</goalstate>'.format(' '.join(str(v) for v in q)) for q in mugiksdrop])
)

def s3():
   r.Release(kb_mug)
   kb_mug.SetTransform(H_from_pose(pose_mugD))
   #r.SetDOFValues([0.,0.,0.,0.],[7,8,9,10]) # open
p3 = openravepy.Planner.PlannerParameters()
p3.SetExtraParameters(''
   + '\n'.join(['<startstate>{}</startstate>'.format(' '.join(str(v) for v in q)) for q in mugiksdrop])
   + '<goalstate>5.759 -1.972 -0.20 1.9 0. 0. 0.</goalstate>\n'
)

plans = [[s1,p1],[s2,p2],[s3,p3]]

if False: # one planner instance

   # create the planner itself
   p = openravepy.RaveCreatePlanner(e, 'OmplCheckMask')
   p.SendCommand('SetOMPLSeed {}'.format(int(sys.argv[1])))

   # do the planning
   for plan in plans:
      s,pp = plan
      s()
      p.InitPlan(r,pp)
      t = openravepy.RaveCreateTrajectory(e, '')
      p.PlanPath(t)
      plan.append(t)

else: # separate instances

   # do the planning
   for plan in plans:
      
      # create the planner itself
      p = openravepy.RaveCreatePlanner(e, 'OmplCheckMask')
      p.SendCommand('SetOMPLSeed {}'.format(int(sys.argv[1])))
      
      s,pp = plan
      s()
      p.InitPlan(r,pp)
      t = openravepy.RaveCreateTrajectory(e, '')
      p.PlanPath(t)
      plan.append(t)

   
   

# retime and execute the trajectories
if e.GetViewer():
   for _,_,t in plans:
      openravepy.planningutils.RetimeActiveDOFTrajectory(t,r,False,1.0,1.0,"","")
   while True:
      print('executing trajectories ...')
      for i,(s,_,t) in enumerate(plans):
         s()
         if i == 0:
            raw_input('press enter to start!')
         r.GetController().SetPath(t);
         while True:
            if r.GetController().IsDone():
               break;
            time.sleep(0.1)
         time.sleep(1)

#p.SendCommand('ListSpaces')

#raw_input('press enter to quit!')