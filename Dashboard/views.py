from os import name
import shutil
import os
from django.core.exceptions import ValidationError
from django.http.response import FileResponse, HttpResponse
from django.shortcuts import redirect, render
from django.http import HttpRequest, request
from pandas.core.indexing import convert_to_index_sliceable
import requests
import json
from requests.exceptions import HTTPError
from django.contrib.auth import login, models, update_session_auth_hash
from django.contrib.auth.models import User
import datetime
import pytz
import threading
import markdown
from . import models as mod
from . import forms 
from django.conf import settings
from django.core.mail import send_mail
import pandas as pd
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
import matplotlib.pyplot as plt
import numpy as np
from io import StringIO
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny


utc=pytz.timezone('Asia/Kolkata')

EMAIL_HOST_USER = 'technologic.itsp@gmail.com'
email_from = EMAIL_HOST_USER

def get_immediate_subdirectories(a_dir):
    return [name for name in os.listdir(a_dir)
            if os.path.isdir(os.path.join(a_dir, name))]

# Create your views here.

def index(request):
    courses_dict = {}
    asgn_remaining_dict = []
    asgn_remaining_dict1 = {}
    try:
        if mod.Profile.objects.filter(user = request.user):
            profile = mod.Profile.objects.get(user = request.user)
        else:
            profile = mod.Profile(user = request.user, email_id=request.user.member.email_id)
            profile.save()
        for course in profile.courses.all():
        
            enrollment = mod.Enrollment.objects.get(profile = profile, course = course)
            total_completed = 0
            total_course = 0
            for assignment in mod.Assignments.objects.filter(course = course) :
                total_course+= 1
                try:
                    x = mod.AssignmentCompleted.objects.get(enrollment = enrollment, assignment = assignment)
                    if not x.isCompleted and assignment.deadline != None:
                        course_var = course.course_name + ": " + assignment.name

                        if enrollment.isTeacher:
                            asgn_remaining_dict1[course_var] = [assignment.name ,assignment.deadline, True , course.course_name]
                        elif enrollment.isAssistant and course.assistant_grading_privilege:
                            asgn_remaining_dict1[course_var] = [assignment.name ,assignment.deadline, True , course.course_name]
                        elif not enrollment.isAssistant:
                            asgn_remaining_dict1[course_var] = [assignment.name ,assignment.deadline, False , course.course_name]
                    else :
                        total_completed+=1
                except Exception as e:
                    print(e)
            if total_course==0:
                courses_dict[course.course_name] = [course.course_info , 100]
            else:
                courses_dict[course.course_name] = [course.course_info , format(total_completed/total_course*100,"0.2f")]
        return render(request,'dashboard.html', {'data' : courses_dict , 'to_do': asgn_remaining_dict , 'to_do_dead': asgn_remaining_dict1})
    except:
        return redirect('signup')

def courses(request, input_course_name = "DEFAULT"):
    if(mod.Courses.objects.filter(course_name = input_course_name)):
        course = mod.Courses.objects.get(course_name = input_course_name)
    profile = mod.Profile.objects.get(user = request.user)
    enrollment = mod.Enrollment.objects.get(profile = profile , course = course)
    data={}
    data['name'] = input_course_name
    data['info'] = course.course_info
    data['isTeacher'] = enrollment.isTeacher or enrollment.isAssistant
    return render(request,'courses.html', data)

def assignments(request, course_name):
    assignment_dict = {}
    content_dict = {}
    course = mod.Courses.objects.get(course_name = course_name)
    enrollment = mod.Enrollment.objects.get(profile = mod.Profile.objects.get(user= request.user), course = course_name)
    if enrollment.isTeacher or (enrollment.isAssistant and course.assistant_grading_privilege):
        teacher = True
    else:
        teacher = False
    if(mod.Assignments.objects.filter(course=course)):
        for asgn in mod.Assignments.objects.all() :
            if(asgn.course == course):
                assignment_dict[asgn.name] = asgn.description
    if(mod.CourseContent.objects.filter(course=course)):
        for content in mod.CourseContent.objects.all() :
            if(content.course == course):
                content_dict[content.name] = content.description
    return render(request,'assignments.html', {'asgn_data' : assignment_dict,'content_data' : content_dict, 'course' : course_name, 'teacher':teacher})

def assignment_submission(request, course_name ,name):
    if request.method == 'POST':
        print("TEST")
        form = forms.AssignmentSubmissionForm(request.POST, request.FILES)
        print(form.is_valid())
        print(form.cleaned_data.get('name'))
        assignment = mod.Assignments.objects.get(course = course_name, name=name)
        if form.is_valid() and assignment.deadline > datetime.datetime.now(tz = utc):
            # enrollment = mod.Enrollment.objects.get(profile = mod.Profile.objects.get(user= request.user), course = course_name)
            for file in request.FILES.getlist('files'):
                file_name = course_name+'/'+name+'/'+ str(request.user)
                file1 = mod.AssignmentFiles(assignment=assignment, file_name = file_name ,file=file, profile = mod.Profile.objects.get(user = request.user))
                file1.save()
            print("all ok")
            id_list = [request.user.member.email_id]
            subject = "Assignment submission for " + name + " in course " + course_name
            message = "Successfully submitted assignment " + name + " in course " + course_name
            t3 = threading.Thread(target=send_email, args=(subject, message, email_from, id_list, None ))  
            t3.start()
            enrollment = mod.Enrollment.objects.get(profile = mod.Profile.objects.get(user= request.user), course = mod.Courses.objects.get(course_name = course_name))
            assigncomplete = mod.AssignmentCompleted.objects.get(enrollment = enrollment , assignment =  assignment)
            assigncomplete.isCompleted = True
            assigncomplete.save()
        elif form.is_valid():
            return render(request, 'assignment_submission.html', {'form' : form, 'asgn_name' : assignment.name, 'asgn' : assignment.description, 'asgn_feedback': "Late submission, closed ",'asgn_grade': "Late ",'asgn_marks' : "NULL", 'asgn_deadline' : assignment.deadline} )
        return redirect('assignments', course_name=course_name ,permanent=True)
    else:
        assignment = mod.Assignments.objects.get(course = course_name, name=name)
        enrollment = mod.Enrollment.objects.get(profile = mod.Profile.objects.get(user= request.user), course = course_name)
        course = mod.Courses.objects.get(course_name = course_name)
        if enrollment.isTeacher==True or (enrollment.isAssistant and course.assistant_grading_privilege):
            return render(request, 'assignment_download.html')
        elif assignment.deadline > datetime.datetime.now(tz = utc):
            asgn_desc = mod.Assignments.objects.get(course = course_name,name=name).description
            form = forms.AssignmentSubmissionForm()
            assignment = mod.Assignments.objects.get(course = course_name, name=name)
            assigncomplete = mod.AssignmentCompleted.objects.get(enrollment = enrollment , assignment =  assignment)
            if mod.AssignmentFiles.objects.filter(assignment = mod.Assignments.objects.get(course = course_name , name = name), profile = mod.Profile.objects.get(user = request.user)):
                asgn_file = mod.AssignmentFiles.objects.filter(assignment = mod.Assignments.objects.get(course = course_name , name = name), profile = mod.Profile.objects.get(user = request.user)).first()
                return render(request, 'assignment_submission.html', {'form' : form,'exists':True, 'asgn' : asgn_desc, 'asgn_feedback': asgn_file.feedback,'asgn_grade': asgn_file.grade, 'asgn_marks': asgn_file.marks,'isCompleted' : assigncomplete.isCompleted,'asgn_deadline' : assignment.deadline})
                # change form above to editable assignment submission
            return render(request, 'assignment_submission.html', {'form' : form,'exists':True ,'asgn_name' : assignment.name, 'asgn' : asgn_desc, 'asgn_feedback': "Submit File for feedback ",'asgn_grade': "Not graded yet",'asgn_marks' : "NULL", 'asgn_deadline' : assignment.deadline} )
        else :
            assignment = mod.Assignments.objects.get(course = course_name, name=name)
            assigncomplete = mod.AssignmentCompleted.objects.get(enrollment = enrollment , assignment =  assignment)
            if mod.AssignmentFiles.objects.filter(assignment = mod.Assignments.objects.get(course = course_name , name = name), profile = mod.Profile.objects.get(user = request.user)):
                asgn_file = mod.AssignmentFiles.objects.filter(assignment = mod.Assignments.objects.get(course = course_name , name = name), profile = mod.Profile.objects.get(user = request.user)).first()
                return render(request, 'assignment_submission.html', {'exists':False, 'asgn' : assignment.description, 'asgn_feedback': asgn_file.feedback,'asgn_grade': asgn_file.grade, 'asgn_marks': asgn_file.marks,'isCompleted' : assigncomplete.isCompleted,'asgn_deadline' : assignment.deadline})
            return render(request, 'assignment_submission.html', {'exists':False, 'asgn_name' : assignment.name, 'asgn' : assignment.description, 'asgn_feedback': "Late",'asgn_grade': "Late",'asgn_marks' : "NULL", 'asgn_deadline' : assignment.deadline} )

def create_barchart(x_data):
    imgdata = StringIO()
    imgdata.truncate(0)
    imgdata.seek(0)
    plt.hist(x_data)
    plt.savefig(imgdata, format='svg')
    imgdata.seek(0)
    data = imgdata.getvalue()
    plt.clf()
    return data 

def content_view(request,course_name,name):
    content = mod.CourseContent.objects.get(course = course_name,name=name)
    return render(request, 'content_view.html', {'content_name':content.name, 'content_desc':content.description})


def assignment_download(request,course_name,name):
    fl_path = 'files/' + course_name + '/' + name
    if request.method=='POST' and os.path.isdir(fl_path):
        output_filename = 'zipped/zip'
        shutil.make_archive(output_filename, 'zip', fl_path)

        zip_file = open(output_filename+'.zip', 'rb')
        return FileResponse(zip_file, filename=course_name+'_'+name+'_submissions.zip')
    else:
        fl_path = 'files/'+course_name+'/'+name
        cmd = "ls './" + fl_path + "'"
        try:
            subs = get_immediate_subdirectories(fl_path)
        except:
            subs = []
        assignment = mod.Assignments.objects.get(course = course_name,name=name)
        asgn_desc = assignment.description
        profile_set = set()
        grades = []
        for sub in mod.AssignmentFiles.objects.filter(assignment = assignment):
            if sub.profile not in profile_set:
                profile_set.add(sub.profile)
                if sub.grade != 'Not graded yet':
                    grades.append(float(sub.grade))
        print(grades)
        if len(grades) > 0 :
            is_graded = True
            grades = np.array(grades)
            mean = np.mean(grades)
            std = np.std(grades)
            plot = create_barchart(grades)
        else:
            is_graded = False
            mean = "Not graded"
            std = "Not graded"
            plot = "Not graded"
        return render(request, 'assignment_download.html', {'asgn' : asgn_desc, 'subs':subs , 'course_name': course_name , 'name':name, 'mean' : mean, 'std':std, 'plot' : plot, 'isgraded' : is_graded })


def assignment_feedback(request,course_name,name):
    if request.method=='POST':
        form = forms.AssignmentFeedbackForm(request.POST, request.FILES)
        if(form.is_valid()):
            assignment = mod.Assignments.objects.get(course = course_name , name = name)
            assignment_files = mod.AssignmentFiles.objects.filter(assignment = assignment)
            file = request.FILES.getlist('feedback_file')[0]
            ds = pd.read_csv(file)
            id_set = set()
            for i in ds.index:
                for assignment_profile in assignment_files.filter(profile = mod.Profile.objects.get(user = ds['name'][i])):
                    assignment_profile.feedback = ds['feedback'][i]
                    assignment_profile.grade = ds['grade'][i]
                    assignment_profile.marks = ds['marks'][i]
                    assignment_profile.save()
                id_set.add( mod.Profile.objects.get(user = ds['name'][i]).email_id )
            allCorrected = True
            for enrollment in mod.Enrollment.objects.filter(course = mod.Courses.objects.get(course_name = course_name), isTeacher = False) :
                if enrollment.isAssistant :
                    continue
                allCorrected = allCorrected and mod.AssignmentCompleted.objects.get(enrollment = enrollment, assignment = assignment).isCompleted
                if not allCorrected :
                   break
            if allCorrected :
                for enrollment in mod.Enrollment.objects.filter(course = mod.Courses.objects.get(course_name = course_name), isTeacher = True) : 
                    x = mod.AssignmentCompleted.objects.get(enrollment = enrollment, assignment = assignment)
                    x.isCompleted = True
                    x.save()
            id_list = list(id_set)
            subject = "Feedback for assignment " + name + " in course " + course_name
            message = "View Feedback on BlueFire moodle"
            t4 = threading.Thread(target=send_email, args=(subject, message, email_from, id_list, None ))  
            t4.start()
            return redirect('assignments', course_name = course_name, permanent = True)
    else :
        form = forms.AssignmentFeedbackForm()
        return render(request,'feedback.html' , {'form': form})


def assignment_creation(request, course_name):
    enrollment = mod.Enrollment.objects.get(profile = mod.Profile.objects.get(user= request.user), course = course_name)
    course = mod.Courses.objects.get(course_name = course_name)
    
    if not (enrollment.isTeacher or (enrollment.isAssistant and course.assistant_creation_privilege)) :
        return redirect('assignments', course_name = course_name,permanent=True)
    print("In here")
    if request.method == 'POST':
        form = forms.AssignmentCreationForm(request.POST)

        if form.is_valid() and form.cleaned_data.get('deadline') > datetime.datetime.now(tz = utc) :
                print(str(form.cleaned_data.get('deadline')))
                print(str(datetime.datetime.now(tz = utc)))
                course1 = mod.Courses.objects.get(course_name = course_name)
                assignment = mod.Assignments(course=course1)
                assignment.name = form.cleaned_data.get('assignment_name')
                assignment.weightage = form.cleaned_data.get('weightage')
                assignment.deadline = form.cleaned_data.get('deadline')
                
                assignment.description = markdown.markdown(form.cleaned_data.get('description'))
                print(markdown.markdown(form.cleaned_data.get('description')))
                assignment.save()

                id_set = set()
                for e in mod.Enrollment.objects.filter(course = course1):
                    profile_e = e.profile
                    mail_e = profile_e.email_id
                    if mail_e:
                        id_set.add(mail_e)
                id_list = list(id_set)
                print(id_list)
                subject = "New assignment created : " + form.cleaned_data.get('assignment_name') + " in course : " + course_name
                message = "Instructor " + str(request.user) + " has added a new assignment " + form.cleaned_data.get('assignment_name') + " in course " + course_name + ". Description :\n"
                html_message = "Instructor " + str(request.user) + " has added a new assignment " + form.cleaned_data.get('assignment_name') + " in course " + course_name + ". Description :<br>"+markdown.markdown(form.cleaned_data.get('description'))
                t2 = threading.Thread(target=send_email, args=(subject, message, email_from, id_list, html_message ))  
                t2.start() 
                e_iter = mod.Enrollment.objects.filter(course = course_name)
                for e in e_iter :
                    x = mod.AssignmentCompleted(enrollment = e, assignment = assignment)
                    x.save()
                    print(x.isCompleted)
                return redirect('assignments', course_name = course_name,permanent=True)
    else:
        form = forms.AssignmentCreationForm()
    return render(request, 'assignment_creation.html',{'form':form})
	
def content_creation(request, course_name):
    enrollment = mod.Enrollment.objects.get(profile = mod.Profile.objects.get(user= request.user), course = course_name)
    course = mod.Courses.objects.get(course_name = course_name)
    if not (enrollment.isTeacher or (enrollment.isAssistant and course.assistant_creation_privilege)) :
        return redirect('assignments', course_name = course_name,permanent=True)
    print("In here")
    if request.method == 'POST':
        form = forms.ContentCreationForm(request.POST)

        if form.is_valid():
            course1 = mod.Courses.objects.get(course_name = course_name)
            content = mod.CourseContent(course=course1)
            content.name = form.cleaned_data.get('content_name')
            print("fine")
            content.description = markdown.markdown(form.cleaned_data.get('description'))
            print(markdown.markdown(form.cleaned_data.get('description')))
            content.save()

            id_set = set()
            for e in mod.Enrollment.objects.filter(course = course1):
                profile_e = e.profile
                mail_e = profile_e.email_id
                if mail_e:
                    id_set.add(mail_e)
            id_list = list(id_set)
            print(id_list)
            subject = "New course content added : " + form.cleaned_data.get('content_name') + " in course : " + course_name
            message = "Instructor " + str(request.user) + " has added new content " + form.cleaned_data.get('content_name') + " in course " + course_name + ". Description :\n"
            html_message = "Instructor " + str(request.user) + " has added new content " + form.cleaned_data.get('content_name') + " in course " + course_name + ". Description :<br>"+markdown.markdown(form.cleaned_data.get('description'))
            t6 = threading.Thread(target=send_email, args=(subject, message, email_from, id_list, html_message ))  
            t6.start() 
            return redirect('assignments', course_name = course_name,permanent=True)
    else:
        form = forms.ContentCreationForm()
    return render(request, 'content_creation.html',{'form':form})



def course_creation(request):
    if request.method == 'POST':
        print("HELLO")
        form = forms.CourseCreationForm(request.POST)
        if form.is_valid():
            print(form.cleaned_data.get('course_name'), form.cleaned_data.get('assistant_can_grade_assignments'))
            try:
                course_added = mod.Courses(course_name = form.cleaned_data.get('course_name'))
                course_added.access_code = form.cleaned_data.get('access_code')
                course_added.master_code = form.cleaned_data.get('master_code')
                course_added.assistant_code = form.cleaned_data.get('assistant_code')
                course_added.course_info = form.cleaned_data.get('course_info')
                course_added.assistant_adding_privilege = form.cleaned_data.get('assistant_can_add_students')
                course_added.assistant_creation_privilege = form.cleaned_data.get('assistant_can_create_assignment')
                course_added.assistant_grading_privilege  = form.cleaned_data.get('assistant_can_grade_assignments')
                course_added.discussion_allowed = True
                course_added.save()
            except Exception as e:
                print("Course already exists, collision!")

            if mod.Profile.objects.filter(user = request.user):
                print("Already Made")
                profile1 = mod.Profile.objects.get(user = request.user)
            else:
                profile1 = mod.Profile(user = request.user, email_id=request.user.member.email_id)
                print("CREATED")
                profile1.save()
                profile1 = mod.Profile.objects.get(user = request.user)

            profile1.courses.add(course_added)
            profile1.save()
            print("HERE")
            print(request.user)
            print(profile1.courses.all()[0])

            if mod.Enrollment.objects.filter(profile = profile1) and mod.Enrollment.objects.filter(course = course_added):
                print("Enrollment Exists")
                enrollment = mod.Enrollment.objects.get(profile = profile1, course = course_added)
                enrollment.isTeacher = True
                enrollment.save()
            else:
                enrollment = mod.Enrollment(profile = profile1)
                enrollment.course = course_added
                enrollment.isTeacher = True
                enrollment.save()

            print(enrollment.profile)
            print(enrollment.course)
            print(enrollment.grade)

        return redirect('dashboard', permanent=True)
    else:
        form = forms.CourseCreationForm()
        return render(request, 'course_creation.html', {'form':form})
        
def course_access(request):
    if request.method == 'POST':
        form = forms.CourseEnrollForm(request.POST)
        if form.is_valid():
            print("In")
            profile = mod.Profile.objects.get(user = request.user)
            if mod.Courses.objects.filter(access_code = form.cleaned_data.get('access_code')):
                course = mod.Courses.objects.filter(access_code = form.cleaned_data.get('access_code')).first()
                print('course',course.course_name,form.cleaned_data.get('master_code'),form.cleaned_data.get('assistant_code'))
                if mod.Enrollment.objects.filter(profile = profile , course= course):
                    print("Already exists, checking for teacher/assistant role")
                    enroll = mod.Enrollment.objects.get(profile = profile , course = course)
                    if(course.master_code == form.cleaned_data.get('master_code')):
                        enroll.isTeacher = True
                        enroll.save()
                    elif(course.assistant_code == form.cleaned_data.get('assistant_code')):
                        enroll.isAssistant = True
                        enroll.save()

                else:
                    enroll = mod.Enrollment(profile = profile , course = course)
                    print(course.master_code,course.assistant_code)
                    if(course.master_code == form.cleaned_data.get('master_code')):
                        enroll.isTeacher = True
                        print('enrolling as teacher')
                        enroll.save()
                    elif(course.assistant_code == form.cleaned_data.get('assistant_code')):
                        enroll.isAssistant = True
                        print('enrolling as assistant')
                        print(course.assistant_grading_privilege)
                        enroll.save()
                    else:
                        enroll.save()
                        for assignment in mod.Assignments.objects.filter(course = course):
                            x = mod.AssignmentCompleted(assignment = assignment , enrollment = enroll)
                            x.save()
                print('Added to course successfully')
            else:
                print('No course exists with access code: ', form.cleaned_data.get('access_code'))
        return redirect('dashboard', permanent = True)
    else:
        form = forms.CourseEnrollForm()
        return render(request , 'course_access.html',{'form': form})

def send_email( subject, message, email_from, recipient_list, html_message ):
    try:
        if html_message:
            send_mail( subject, message, email_from, recipient_list, html_message=html_message ) 
        else :
            send_mail( subject, message, email_from, recipient_list ) 
        print('success', recipient_list)
    except :
        print('Email failed')

def course_email(request, course_name):
    enrollment = mod.Enrollment.objects.get(profile=mod.Profile.objects.get(user = request.user), course=mod.Courses.objects.get(course_name = course_name))
    course = mod.Courses.objects.get(course_name = course_name)
    if request.method == 'POST':
        form = forms.CourseEmailForm(request.POST)
        if form.is_valid():
            if enrollment.isTeacher or (enrollment.isAssistant and course.assistant_adding_privilege) :
                course = mod.Courses.objects.get(course_name=course_name)
                email_list = [s.strip() for s in form.cleaned_data.get('email_list').split(",")]
                message = 'Hi. This is an email giving you access to course '+course_name+'. Your access code is : ' + course.access_code
                if form.cleaned_data.get('assistant_email'):
                    message = 'Hi. This is an email giving you access to course '+course_name+'. Your access code is : ' + course.access_code + '. Your assistant code is : ' + course.assistant_code
                if form.cleaned_data.get('master_email'):
                    message = 'Hi. This is an email giving you access to course '+course_name+'. Your access code is : ' + course.access_code + '. Your master code is : ' + course.master_code
                subject = 'Course access code for course '+course_name
                recipient_list = email_list
                t1 = threading.Thread(target=send_email, args=(subject, message, email_from, recipient_list, None,  ))  
                t1.start()         
        return redirect('dashboard', permanent = True)
    else:
        if enrollment.isTeacher or (enrollment.isAssistant and course.assistant_adding_privilege) :
            form = forms.CourseEmailForm()
            return render(request , 'course_email.html',{'form': form})   
        else:
            return redirect('dashboard', permanent = True)

def create_boxchart(data, ticks):
    imgdata = StringIO()
    imgdata.truncate(0)
    imgdata.seek(0)
    plt.boxplot(data)
    plt.xticks([i for i in range(1,len(ticks)+1)], ticks)
    plt.savefig(imgdata, format='svg')
    imgdata.seek(0)
    data = imgdata.getvalue()
    plt.clf()
    return data 

def course_stats(request, course_name):
    enrollment = mod.Enrollment.objects.get(profile=mod.Profile.objects.get(user = request.user), course=mod.Courses.objects.get(course_name = course_name))
    course = course=mod.Courses.objects.get(course_name = course_name)
    assignment_stats_dict = {}
    assignment_names = []
    assignment_grades = []
    chart = ""
    
    for assignment in mod.Assignments.objects.filter(course = course):
        grades = []
        profile_set = set()
        for sub in mod.AssignmentFiles.objects.filter(assignment = assignment):
            if sub.profile not in profile_set:
                profile_set.add(sub.profile)
                if sub.grade != 'Not graded yet':
                    grades.append(float(sub.grade))
        # print(grades)
        assignment_names.append(assignment.name)
        assignment_grades.append(grades)
        if len(grades) !=0 :
            assignment_stats_dict[assignment.name] = "Mean : " + str(np.mean(grades)) + " Std : " + str(np.std(grades))
        chart = create_boxchart(assignment_grades, assignment_names)
        # print(chart,'chart')
        # print(assignment_stats_dict)
    if enrollment.isTeacher or enrollment.isAssistant:
        return render(request, 'course_stats.html', {'course_name' : course_name, 'assignment_dict' : assignment_stats_dict, 'chart':chart})
    else:
         return render(request, 'course_stats.html', {'course_name' : course_name, 'assignment_dict' : assignment_stats_dict})

def stop_announcements(request, course_name):
    course = mod.Courses.objects.get(course_name = course_name)
    course.discussion_allowed = False
    course.save()
    return announcements(request, course_name)

def start_announcements(request, course_name):
    course = mod.Courses.objects.get(course_name = course_name)
    course.discussion_allowed = True
    course.save()
    return announcements(request, course_name)

def announcements_create(request, course_name):
    enrollment = mod.Enrollment.objects.get(profile = mod.Profile.objects.get(user= request.user), course = course_name)
    course = mod.Courses.objects.get(course_name = course_name)
    # if not (enrollment.isTeacher or (enrollment.isAssistant and course.assistant_creation_privilege)) :
        # this means that student is present, or TA with less privileges
    #     return redirect('assignments', course_name = course_name,permanent=True)
    # print("In here")
    if request.method == 'POST':
        form = forms.AnnouncementCreationForm(request.POST)
        if form.is_valid():
            course1 = mod.Courses.objects.get(course_name = course_name)
            message = mod.Message(course=course1)
            message.content = markdown.markdown(form.cleaned_data.get('content'))
            message.time_of_last_edit = datetime.datetime.now()
            message.date_time_of_last_edit = datetime.datetime.now()
            message.author = mod.Profile.objects.get(user = request.user)
            message.save()
            print("fine")
            return redirect('announcements', course_name = course_name,permanent=True)
    else:
        form = forms.AnnouncementCreationForm()
        return render(request,'announcements_new.html',{'form':form})


def announcements(request, course_name):
    announcement_dict = {}
    course = mod.Courses.objects.get(course_name = course_name)
    enrollment = mod.Enrollment.objects.get(profile = mod.Profile.objects.get(user= request.user), course = course_name)
    if enrollment.isTeacher or (enrollment.isAssistant):
        teacher = True
    else:
        teacher = False
    if(mod.Message.objects.filter(course=course)):
        for parent_post in mod.Message.objects.filter(course = course):
                current_message = (parent_post.content, parent_post.id, parent_post.author, str(parent_post.date_time_of_last_edit+datetime.timedelta(hours=5.5))[:-13])
                announcement_dict[current_message] = []
                for reply in mod.Replies.objects.filter(parent_message = parent_post):
                    announcement_dict[current_message].append((reply.content, reply.author, str(reply.date_time_of_last_edit+datetime.timedelta(hours=5.5))[:-13]))
    allowed = course.discussion_allowed
    return render(request,'announcements.html', {'data' : announcement_dict, 'course' : course_name, 'teacher':teacher, 'allowed':allowed})

def announcements_reply(request, course_name, id):
    if request.method == 'POST':
        form = forms.ReplyCreationForm(request.POST)
        if form.is_valid():
            message = mod.Message.objects.get(id = id)
            reply = mod.Replies(parent_message = message)
            reply.content = markdown.markdown(form.cleaned_data.get('content'))
            reply.time_of_last_edit = datetime.datetime.now()
            reply.date_time_of_last_edit = datetime.datetime.now()
            reply.author = mod.Profile.objects.get(user = request.user)
            reply.course = message.course
            reply.save()
            print("fine")
            return redirect('announcements', course_name = course_name,permanent=True)
    else:
        form = forms.ReplyCreationForm()
        return render(request,'announcements_new.html',{'form':form})

def participants(request, course_name):
    course = mod.Courses.objects.get(course_name = course_name)
    members = {}
    for mem in mod.Enrollment.objects.filter(course = course):
        if mem.isTeacher : 
            members[mem.profile.user] = 'Teacher'
        elif mem.isAssistant:
            members[mem.profile.user] = 'Teaching Assistant'
        else:
            members[mem.profile.user] = 'Student'
    return render(request,'participants.html',{'participants':members, 'course':course_name})

def grades(request, course_name):
    enrollment = mod.Enrollment.objects.get(profile=mod.Profile.objects.get(user = request.user), course=mod.Courses.objects.get(course_name = course_name))
    course =mod.Courses.objects.get(course_name = course_name)
    grades = {}
    course_total=0
    grand_total = 0
    warning=""
    # This calculation is for the student
    if not (enrollment.isTeacher or enrollment.isAssistant):
        for assignment in mod.Assignments.objects.filter(course = course):
            profile_set = set()
            for sub in mod.AssignmentFiles.objects.filter(assignment = assignment, profile = mod.Profile.objects.get(user = request.user)):
                if sub.profile not in profile_set:
                    profile_set.add(sub.profile)
                    if sub.grade != 'Not graded yet':
                        grades[assignment.name] = sub.marks
                        course_total+=sub.marks*assignment.weightage
                        grand_total += assignment.weightage
        course_total /= 100
        enrollment.marks = course_total

        if(enrollment.marks<grand_total/3):
            warning = "Your score is below 33% of the total"
    else:
        count=0
        for assignment in mod.Assignments.objects.filter(course = course):
            profile_set = set()
            for sub in mod.AssignmentFiles.objects.filter(assignment = assignment):
                if sub.profile not in profile_set:
                    profile_set.add(sub.profile)
                    if sub.grade != 'Not graded yet':
                        grades[assignment.name] += sub.marks
                        course_total+=sub.marks*assignment.weightage
                        grand_total += assignment.weightage
                        count+=1
            grades[assignment.name]/=count
        course_total/=count
        course_total /= 100
        enrollment.marks = course_total
        course.class_average = course_total

    print("joiefje")
    
    return render(request,'grades.html',{'grades':grades, 'course_name':course_name, 'course_total':course_total, 'warning':warning, 'grand_total' : grand_total})


def message_list(request):
    profile1 = mod.Profile.objects.get(user = request.user)   
    if request.method == 'POST':
        form = forms.MessageSearchForm(request.POST)
        if form.is_valid():
            receiver = form.cleaned_data.get('username')
            if not request.user==receiver:
                if mod.Profile.objects.filter(user = receiver) :
                    print("valid hi tha")
                    profile2 = mod.Profile.objects.get(user = receiver)
                    if not ( mod.Conversation.objects.filter(person1 = profile1, person2 = profile2) or mod.Conversation.objects.filter(person1 = profile2, person2 = profile1) ) :
                        conversation = mod.Conversation(person1 = profile1, person2 = profile2)
                        conversation.save()
    form = forms.MessageSearchForm()
    convo_list = []
    for convo in mod.Conversation.objects.filter(person1 = profile1):
        convo_list.append(convo.person2.user)
    for convo in mod.Conversation.objects.filter(person2 = profile1):
        convo_list.append(convo.person1.user)
    return render(request, 'message_list.html', {'form':form, 'list' : convo_list})


def chat_screen(request, person):
    profile1 = mod.Profile.objects.get(user = request.user)
    receiver_person = mod.Profile.objects.get(user = person )
    chat_list = []
    sender = True
    if request.method == 'POST':
        form = forms.AddChat(request.POST)
        if form.is_valid():
            chat_message = form.cleaned_data.get('chat_message')
            if mod.Conversation.objects.filter(person1 = profile1, person2 = receiver_person):
                sender = False
                conversation =  mod.Conversation.objects.get(person1 = profile1, person2 = receiver_person)
                if conversation.messages == None:
                    conversation.senders= []
                    conversation.times= []
                    conversation.dates_and_times = []
                    conversation.messages = []
                conversation.senders.append(True)
                conversation.times.append(datetime.datetime.now())
                conversation.dates_and_times.append(datetime.datetime.now())
                conversation.messages.append(chat_message)
                conversation.save()
                length = len(conversation.messages)
                for index in range(length):
                    chat_list.append((conversation.messages[index],conversation.senders[index],conversation.dates_and_times[index]))
            elif mod.Conversation.objects.filter(person1 = receiver_person, person2 = profile1 ):
                conversation =  mod.Conversation.objects.get(person1 = receiver_person, person2 = profile1)
                if conversation.messages == None:
                    conversation.senders= []
                    conversation.dates_and_times = []
                    conversation.times= []
                    conversation.messages = []
                conversation.senders.append(False)
                conversation.times.append(datetime.datetime.now())
                conversation.dates_and_times.append(datetime.datetime.now())
                conversation.messages.append(chat_message)
                conversation.save()
                length = len(conversation.messages)
                for index in range(length):
                    chat_list.append((conversation.messages[index],conversation.senders[index],conversation.dates_and_times[index]))
            else:
                print(chat_message)
    else:
        if mod.Conversation.objects.filter(person1 = profile1, person2 = receiver_person):
            sender = False
            conversation =  mod.Conversation.objects.get(person1 = profile1, person2 = receiver_person)
            if conversation.messages == None:
                conversation.senders= []
                conversation.dates_and_times = []
                conversation.times= []
                conversation.messages = []
            length = len(conversation.messages)
            for index in range(length):
                chat_list.append((conversation.messages[index],conversation.senders[index],conversation.dates_and_times[index]))
        elif mod.Conversation.objects.filter(person1 = receiver_person, person2 = profile1 ):
            conversation =  mod.Conversation.objects.get(person1 = receiver_person, person2 = profile1)
            if conversation.messages == None:
                conversation.senders= []
                conversation.dates_and_times = []
                conversation.times= []
                conversation.messages = []        
            length = len(conversation.messages)
            for index in range(length):
                chat_list.append((conversation.messages[index],conversation.senders[index],conversation.dates_and_times[index]))
    form = forms.AddChat()
    return render(request, 'chat_list.html', {'form':form, 'chat_list' : chat_list, 'is_sender' : sender })


def profile(request):
    courses_list=[]
    try:
        profile = mod.Profile.objects.get(user = request.user)
        for course in profile.courses.all():
            courses_list.append(course.course_name)
    except Exception as e:
        print(e)
    return render(request,'profile.html', {'courses_list': courses_list})

def settings(request):
    return render(request,'settings.html') 

def add_course(request, sample_input):
    if(mod.Courses.objects.filter(course_name = "trial 1a")):
        course1 = mod.Courses.objects.get(course_name = "trial 1a")
    else:
        course1 = mod.Courses(course_name = "trial 1a")
        course1.save()
    if mod.Profile.objects.filter(user = "prats"):
        print("Already Made")
        profile1 = mod.Profile.objects.get(user = "prats")
    else:
        profile1 = mod.Profile(user = "prats")
        profile1.save()

    profile1.courses.add(course1)
    profile1.save()
    print("HERE")
    print(request.user)
    print(profile1.courses.all()[0])
    print(sample_input)

    if mod.Enrollment.objects.filter(profile = profile1) and mod.Enrollment.objects.filter(course = course1):
        print("Enrollment Exists")
        enrollment = mod.Enrollment.objects.get(profile = profile1, course = course1)
    else:
        enrollment = mod.Enrollment(profile = profile1)
        enrollment.course = course1
        enrollment.save()

    print(enrollment.profile)
    print(enrollment.course)
    print(enrollment.grade)
    data = {
        "profileq":profile1.courses.all(),
        "course":course1.profile_set.all(),
    }
    return render(request, 'courses.html', data)


# @csrf_exempt
# @api_view(["POST", "GET"])
# @permission_classes((AllowAny,))
# def login(request):
#     username = request.data.get("username")
#     password = request.data.get("password")
#     if username is None or password is None:
#         return Response({'error': 'Please provide both username and password'},
#                         status=HTTP_400_BAD_REQUEST)
#     user = authenticate(username=username, password=password)
#     if not user:
#         return Response({'error': 'Invalid Credentials'},
#                         status=HTTP_404_NOT_FOUND)
#     request.session.save()
#     return Response({'Success': 'Logged in'},
#                     status=HTTP_200_OK)


@api_view(["POST"])
@permission_classes([AllowAny]) 
def rest_courses(request):
    if rest_login(request):
        profile = mod.Profile.objects.get(user = request.data.get("username"))
        courses_list = []
        for course in profile.courses.all():
            courses_list.append(course.course_name)
        Res = {'courses' : courses_list}
        return Response(Res)
    else:
        raise ValidationError({"400": f'Some Problem'})

@api_view(["POST"])
@permission_classes([AllowAny]) 
def rest_submit_assignment(request):
    if rest_login(request):
        user_name = request.data.get("username")
        profile = mod.Profile.objects.get(user = user_name)
        course_name = request.data.get('course_name')
        if mod.Enrollment.objects.get(profile = mod.Profile.objects.get(user = user_name), course = mod.Courses.objects.get(course_name = course_name)):
            asgn_name = request.data.get('asgn_name')
            assignment = mod.Assignments.objects.get(course = course_name , name = asgn_name)
            for file in request.FILES.getlist('file'):
                    file_name = course_name+'/'+asgn_name+'/'+ user_name
                    file1 = mod.AssignmentFiles(assignment=assignment, file_name = file_name ,file=file, profile = profile)
                    file1.save()
            id_list = [profile.email_id]
            subject = "Assignment submission for " + asgn_name + " in course " + course_name
            message = "Successfully submitted assignment " + asgn_name + " in course " + course_name
            t3 = threading.Thread(target=send_email, args=(subject, message, email_from, id_list, None ))  
            t3.start()
            enrollment = mod.Enrollment.objects.get(profile = mod.Profile.objects.get(user= request.user), course = mod.Courses.objects.get(course_name = course_name))
            assigncomplete = mod.AssignmentCompleted.objects.get(enrollment = enrollment , assignment =  assignment)
            assigncomplete.isCompleted = True
            assigncomplete.save()
            Res = {'Assignment'+asgn_name: "Done"}
            return Response(Res)
        else:
            return Response('Error')
    else:
        raise ValidationError({"400": f'Some Problem'})

@api_view(["POST"])
@permission_classes([AllowAny]) 
def rest_todolist(request):
    if rest_login(request):
        profile = mod.Profile.objects.get(user = request.data.get("username"))
        asgn_remaining_dict1= {}
        for course in profile.courses.all():
            enrollment = mod.Enrollment.objects.get(profile = profile, course = course)
            for assignment in mod.Assignments.objects.filter(course = course):
                try:
                    x = mod.AssignmentCompleted.objects.get(enrollment = enrollment, assignment = assignment)
                    if not x.isCompleted and assignment.deadline != None:
                        course_var = course.course_name + ": " + assignment.name
                        if enrollment.isTeacher:
                            asgn_remaining_dict1[course_var] = [assignment.name ,assignment.deadline, course.course_name]
                        elif enrollment.isAssistant and course.assistant_grading_privilege:
                            asgn_remaining_dict1[course_var] = [assignment.name ,assignment.deadline, course.course_name]
                        elif not enrollment.isAssistant:
                            asgn_remaining_dict1[course_var] = [assignment.name ,assignment.deadline, course.course_name]
                except Exception as e:
                    print(e)
        Res = {'todo' : asgn_remaining_dict1}
        return Response(Res)
    else:
        raise ValidationError({"400": f'Some Problem'})


@api_view(["POST"])
@permission_classes([AllowAny]) 
def rest_feedback(request):
    if rest_login(request):
        profile = mod.Profile.objects.get(user = request.data.get("username"))
        ds = pd.read_csv(request.FILES.getlist('upload_file')[0])
        id_set = set()
        course_name = request.data.get('course_name')
        course = mod.Courses.objects.get(course_name = course_name)
        asgn_name = request.data.get('asgn_name')
        if mod.Enrollment.objects.get(profile = profile, course = mod.Courses.objects.get(course_name = course_name)): 
            enrollment = mod.Enrollment.objects.get(profile = profile, course = mod.Courses.objects.get(course_name = course_name))
        else :
            return Response('Error')
        if enrollment.isTeacher or (enrollment.isAssistant and course.assistant_grading_privilege):
            pass
        else:
            return Response('Error')
        assignment = mod.Assignments.objects.get(course = course_name , name = asgn_name)
        assignment_files = mod.AssignmentFiles.objects.filter(assignment = assignment)
        for i in ds.index:
                    for assignment_profile in assignment_files.filter(profile = mod.Profile.objects.get(user = ds['name'][i])):
                        assignment_profile.feedback = ds['feedback'][i]
                        assignment_profile.grade = ds['grade'][i]
                        assignment_profile.marks = ds['marks'][i]
                        assignment_profile.save()
                    id_set.add( mod.Profile.objects.get(user = ds['name'][i]).email_id )
        allCorrected = True
        for enrollment in mod.Enrollment.objects.filter(course = mod.Courses.objects.get(course_name = course_name), isTeacher = False) :
                    if enrollment.isAssistant :
                        continue
                    allCorrected = allCorrected and mod.AssignmentCompleted.objects.get(enrollment = enrollment, assignment = assignment).isCompleted
                    if not allCorrected :
                        break
        if allCorrected :
                    for enrollment in mod.Enrollment.objects.filter(course = mod.Courses.objects.get(course_name = course_name), isTeacher = True) : 
                        x = mod.AssignmentCompleted.objects.get(enrollment = enrollment, assignment = assignment)
                        x.isCompleted = True
                        x.save()
        id_list = list(id_set)
        subject = "Feedback for assignment " + asgn_name + " in course " + course_name
        message = "View Feedback on BlueFire moodle"
        t7 = threading.Thread(target=send_email, args=(subject, message, email_from, id_list, None ))  
        t7.start()
        Res = 'Success'
        return Response(Res)
    else:
        raise ValidationError({"400": f'Some Problem'})
    
@api_view(["POST"])
@permission_classes([AllowAny]) 
def rest_assignment_download(request):
    course_name = request.data.get('course_name')
    asgn_name = request.data.get('asgn_name')
    username = request.data.get('username')
    profile = mod.Profile.objects.get(user = username)
    enrollment = mod.Enrollment.objects.get(profile = profile, course = course_name)
    if enrollment.isTeacher or (enrollment.isAssistant and mod.Courses.objects.get(course_name=course_name).assistant_grading_privilege):
        fl_path = 'files/' + course_name + '/' + asgn_name
        if os.path.isdir(fl_path):
            output_filename = 'zipped/zip'
            shutil.make_archive(output_filename, 'zip', fl_path)
            zip_file = open(output_filename+'.zip', 'rb')
            return FileResponse(zip_file, filename=course_name+'_'+name+'_submissions.zip')
        else:
            raise ValidationError({"400": f'No Submissions'})

    else:
        raise ValidationError({"400": f'You do not have access to this command'})

def rest_login(request):
    data = {}
    # reqBody = json.loads(request.body)
    print(request)
    username = request.data.get("username")
    password = request.data.get('password')
    try:
        Account = User.objects.get(username=username)
    except BaseException as e:
        raise ValidationError({"400": f'{str(e)}'})
    token = Token.objects.get_or_create(user=Account)[0].key
    print(token)
    if not Account.check_password(password):
        raise ValidationError({"message": "Incorrect Login credentials"})
    if Account:
        if Account.is_active:
            login(request, Account)
            request.session.save()
            return True
        else:
            return False

    else:
        return False



# @api_view(['GET'])
# def rest_courses(request):
#     if request.method == 'GET':
#         print(request.user)
#         return Response(str(request.user))
#     else :
#         return Response('SG')



def create_profile():
    new_profile = mod.Profile(user = request.user, email_id=request.user.member.email_id)
    new_profile.save()
    ##To be called only after signup and nowhere else

def create_course(name):
    new_course = mod.Courses(course_name = name)
    new_course.save()
    ###Store master variable inside the course_user pair

def add_course_to_profile(course_name):
    #called means verified to add, profile made and course exists
    profile = mod.Profile.objects.get(user = request.user)
    profile.courses.add(course_name)

def verify_access_code(input_course_name, access_code):
    # course exists is a prerequisite
    course = mod.Courses.objects.get(course_name = input_course_name)
    if course.code==access_code:
        return True
    else:
        return False

def grant_master_role(input_course_name, access_code):
    # course exists is a prerequisite
    course = mod.Courses.objects.get(course_name = input_course_name)
    if course.master_code==access_code:
        return True
    else:
        return False
#Need to store master_code variable inside the course


def edit_profile(request):
    if request.method == 'POST':
        form = forms.EditProfile(request.POST)
        if form.is_valid():
            if form.cleaned_data.get('email_id') != '':
                request.user.member.email_id = form.cleaned_data.get('email_id')
            if form.cleaned_data.get('institute_name') != '':
                request.user.member.institute_name = form.cleaned_data.get('institute_name')
            request.user.save()
        return redirect('profile', permanent = True) 
    else:
        form = forms.EditProfile()
#        form.email_id = request.user.member.email_id
#        form.institute_name = request.user.member.institute_name
#        form.fields['email_id'].initial = request.user.member.email_id
#        form.fields['institute_name'].initial = request.user.member.institute_name
        context = {'form': form}
        return render(request , 'settings.html', context) 



def GUI_grader(request, course_name, name, student_name):
    if request.method == 'POST':
        form = forms.GUIGrader(request.POST)
        student = mod.Profile.objects.get(user = student_name)
        course = mod.Courses.objects.get(course_name = course_name)
        assignment = mod.Assignments.objects.get(course = course, name = name)
        assignment_file = mod.AssignmentFiles.objects.filter(profile = student, assignment = assignment)
        if form.is_valid():
            for assignment_profile in assignment_file:
                assignment_profile.feedback = form.cleaned_data.get('feedback')
                assignment_profile.marks = form.cleaned_data.get('marks')
                assignment_profile.grade = form.cleaned_data.get('grade')
                assignment_profile.save()
        allCorrected = True
        for enrollment in mod.Enrollment.objects.filter(course = course, isTeacher = False) :
            allCorrected = allCorrected and mod.AssignmentCompleted.objects.get(enrollment = enrollment, assignment = assignment).isCompleted
            if not allCorrected :
                break
        if allCorrected :
            for enrollment in mod.Enrollment.objects.filter(course = course, isTeacher = True) : 
                x = mod.AssignmentCompleted.objects.get(enrollment = enrollment, assignment = assignment)
                x.isCompleted = True
                x.save()

        return redirect('assignment_download', name = name , course_name = course_name,  permanent = True) 
    else:
        form = forms.GUIGrader()
        context = {'form': form}
        print("my nm")
        return render(request , 'GUI_grader.html', context) 



def edit_deadline(request , course_name, name):
    if request.method == 'POST':
        form = forms.EditDeadline(request.POST)
        if form.is_valid() and form.cleaned_data.get('deadline') > datetime.datetime.now(tz = utc):
            course = mod.Courses.objects.get(course_name = course_name)
            assignment = mod.Assignments.objects.get(course = course , name = name)
            assignment.deadline = form.cleaned_data.get('deadline')
            assignment.save()
            return redirect('assignment_download',course_name = course_name, name=name, permanent = True) 
        else:      
            return render(request , 'edit_deadline.html', {'form':form}) 
    else:
        form = forms.EditDeadline()
        context = {'form': form}
        return render(request , 'edit_deadline.html', context) 




