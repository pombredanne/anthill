from django.views.generic.list_detail import object_list, object_detail
from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.http import HttpResponseForbidden
from django.template import RequestContext
from django.template.loader import render_to_string
from tagging.views import tagged_object_list
from anthill.projects.models import Project, Role, Ask
from anthill.projects.forms import ProjectForm, LinkFormSet, RoleFormSet, FeedFormSet, JoinProjectForm
from feedinator.models import Feed

def projects(request):
    """
        Combined view of latest projects

        Template: projects/projects.html

        Context:
            projects - Latest projects
    """
    project_qs = Project.objects.select_related().order_by('-update_date').all()
    if hasattr(project_qs, '_gatekeeper'):
        project_qs = project_qs.approved()
    context = {'projects': project_qs[:5],}
    return render_to_response('projects/projects.html', context,
                              context_instance=RequestContext(request))

def archive(request, projects='all'):
    """
        Paginated listing of ``Project``s.

        Template: projects/projects_list.html

        Context:
            projects     - 'all'/'official'/'community'
            project_list - list of projects

            See ``django.views.generic.list_detail.object_list`` for pagination variables.
    """
    qs = Project.objects.select_related().order_by('-update_date')
    if projects == 'official':
        qs = qs.filter(official=True)
    elif projects == 'community':
        qs = qs.filter(official=False)
    if hasattr(qs, '_gatekeeper'):
        qs = qs.approved()
    return object_list(request, queryset=qs,
                       template_object_name='project', allow_empty=True,
                       extra_context={'projects':projects}, paginate_by=10)

def tag_archive(request, tag):
    """
        Paginated listing of ``Project``s by tag.

        Template: projects/projects_list.html

        Context:
            tag          - tag being displayed
            project_list - list of projects

            See ``django.views.generic.list_detail.object_list`` for pagination variables.
    """
    qs = Project.objects.select_related()
    if hasattr(qs, '_gatekeeper'):
        qs = qs.approved()
    return tagged_object_list(request, qs, tag, paginate_by=10,
                              template_object_name='project',
                              extra_context={'tag':tag},
                              allow_empty=True)

def project_detail(request, slug):
    """
        Detail view of a ``Project``.

        Template: projects/project_detail.html

        Context:
            project - ``Project`` instance
    """
    # explicitly don't use _gatekeeper check here
    return object_detail(request,
                         queryset=Project.objects.select_related().all(),
                         slug=slug, template_object_name='project')

@login_required
def new_project(request):
    """
        Creation of new project.

        Template: projects/new_project.html

        Context:
            project_form - ``ProjectForm`` instance
    """
    if request.method == 'GET':
        project_form = ProjectForm()
    else:
        project_form = ProjectForm(request.POST)
        if project_form.is_valid():
            project = project_form.save(commit=False)
            project.lead = request.user
            project.save()
            messages.success(request, 'Your project has been created.')
            return redirect('edit_project', project.slug)
    return render_to_response('projects/new_project.html',
                              {'project_form':project_form},
                              context_instance=RequestContext(request))

@login_required
def edit_project(request, slug):
    """
        Editing of existing project

        Template: projects/edit_project.html

        Context:
            project      - ``Project`` instance being edited
            project_form - ``ProjectForm`` instance
            role_formset - ``RoleFormSet`` instance for project
            link_formset - ``LinkFormSet`` instance for project
            feed_formset - ``FeedFormSet`` instance for project
    """
    qs = Project.objects.all()
    if hasattr(qs, '_gatekeeper'):
        qs = qs.approved()
    project = get_object_or_404(qs, slug=slug)
    if request.user != project.lead and not request.user.is_staff:
        return HttpResponseForbidden('Only the project lead can edit a project.')

    if request.method == 'GET':
        project_form = ProjectForm(instance=project)
        link_formset = LinkFormSet(instance=project, prefix='links')
        role_formset = RoleFormSet(instance=project, prefix='roles')
        feed_data = [{'id':s.feed.id, 'title':s.feed.title, 'url':s.feed.url}
                     for s in project.subscriptions.all()]
        feed_formset = FeedFormSet(prefix='feeds', initial=feed_data)
    else:
        project_form = ProjectForm(request.POST, instance=project)
        link_formset = LinkFormSet(request.POST, instance=project, prefix='links')
        role_formset = RoleFormSet(request.POST, instance=project, prefix='roles')
        feed_formset = FeedFormSet(request.POST, prefix='feeds')

        # only save if the main form + all three formsets validate
        if (project_form.is_valid() and link_formset.is_valid() 
            and role_formset.is_valid() and feed_formset.is_valid()):

            # three simple saves do so much
            project_form.save()
            link_formset.save()
            role_formset.save()

            # update or create feeds
            for form in feed_formset.forms:
                data = dict(form.cleaned_data)
                if data and not data['DELETE']:
                    feed_id = data.pop('id')
                    data.pop('DELETE')
                    if feed_id:
                        Feed.objects.filter(pk=feed_id).update(**data)
                    else:
                        feed = Feed.objects.create(**data)
                        project.subscriptions.create(feed=feed)

            # delete feeds in deleted_forms
            del_ids = [f.cleaned_data['id'] for f in feed_formset.deleted_forms]
            Feed.objects.filter(pk__in=del_ids).delete()

            messages.success(request, 'Your changes have been saved.')
            return redirect(project)

    # display on GET or failed POST
    return render_to_response('projects/edit_project.html',
                              {'project':project, 'project_form':project_form,
                               'role_formset': role_formset,
                               'link_formset': link_formset,
                               'feed_formset': feed_formset,},
                              context_instance=RequestContext(request))

@login_required
def join_project(request, slug):
    """
        Request to join a project.

        Template: projects/join_project.html

        Context:
            project - Project user is requesting to join
            form - ``JoinProjectForm`` instance
    """
    qs = Project.objects.all()
    if hasattr(qs, '_gatekeeper'):
        qs = qs.approved()
    project = get_object_or_404(qs, slug=slug)
    if request.method == 'GET':
        form = JoinProjectForm()
    else:
        form = JoinProjectForm(request.POST)
        if form.is_valid():
            if Role.objects.filter(user=request.user, project=project).count():
                messages.error(request, 'You already have a pending request to join this project.')
            else:
                role = Role.objects.create(user=request.user, project=project,
                                           message=form.cleaned_data['message'])

                subject = render_to_string('projects/join_request_subject.txt',
                                           {'project':project})
                body = render_to_string('projects/join_request_email.txt',
                                        {'project': project, 'role': role})
                project.lead.email_user(subject, body)
                messages.success(request, 'Thank you for submitting your request to join %s' % project)
                return redirect(project.get_absolute_url())

    return render_to_response('projects/join_project.html',
                              {'project':project, 'form':form},
                             context_instance=RequestContext(request))

def _user_on_project(project, user):
    ''' check if user is a current project member '''
    allowed_users = list(project.roles.exclude(status='R')
                         .values_list('user_id', flat=True))
    allowed_users.append(project.lead_id)
    return user.id in allowed_users

@login_required
@require_POST
def add_ask(request, slug):
    """ POST view for adding 'Asks' """
    project = get_object_or_404(Project, slug=slug)
    message = request.POST['message']

    if _user_on_project(project, request.user):
        Ask.objects.create(message=message, project=project, user=request.user)
        return redirect(project)
    else:
        return HttpResponseForbidden('Only project members may post asks')

@login_required
@require_POST
def delete_ask(request, id):
    """ POST view for deleting 'Asks' """
    ask = get_object_or_404(Ask, pk=id)
    if _user_on_project(ask.project, request.user):
        ask.delete()
        return redirect('edit_project', ask.project.slug)
    else:
        return HttpResponseForbidden('Only project members may delete tasks')

def ask_list(request):
    """
        Paginated listing of ``Ask``s.

        Template: projects/ask_list.html

        Context:
            ask_list - list of asks

            See ``django.views.generic.list_detail.object_list`` for pagination variables.
    """
    return object_list(request,
                       queryset=Ask.objects.select_related().all(),
                       template_object_name='ask', allow_empty=True,
                       paginate_by=20)
