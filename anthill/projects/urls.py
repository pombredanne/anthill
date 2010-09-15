from django.conf.urls.defaults import *
from anthill.projects.feeds import ProjectFeed, AskFeed

urlpatterns = patterns('',
    url(r'^feeds/(?P<url>.*)/$', 'django.contrib.syndication.views.feed',
        {'feed_dict': {'latest': ProjectFeed, 'asks': AskFeed}},
        name='project_feeds'),
)

urlpatterns += patterns('anthill.projects.views',
    url(r'^$', 'projects', name='projects'),
    url(r'^all/$', 'archive', name='all_projects'),
    url(r'^official/$', 'archive', {'projects':'official'},
        name='official_projects'),
    url(r'^community/$', 'archive', {'projects':'community'},
        name='community_projects'),
    url(r'^asks/$', 'ask_list', name='all_project_asks'),
    url(r'^new/$', 'new_project', name='new_project'),
    url(r'^tag/(?P<tag>[^/]+)/$', 'tag_archive', name='projects_tagged'),
    url(r'^delete_ask/(?P<id>\d+)/$', 'delete_ask', name='delete_ask'),
    url(r'^(?P<slug>[-\w]+)/$', 'project_detail', name='project_detail'),
    url(r'^(?P<slug>[-\w]+)/edit/$', 'edit_project', name='edit_project'),
    url(r'^(?P<slug>[-\w]+)/join/$', 'join_project', name='join_project'),
    url(r'^(?P<slug>[-\w]+)/add_ask/$', 'add_ask', name='new_project_ask'),
)
