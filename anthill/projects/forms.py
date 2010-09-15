from django import forms
from django.forms.formsets import formset_factory
from django.forms.models import inlineformset_factory
from django.template.defaultfilters import slugify
from anthill.projects.models import Project, Link, Role

def _slugify(name, Model):
    base_slug = slugify(name)
    slug = base_slug
    n = 1
    while Model.objects.filter(slug=slug).count():
        slug = '%s-%s' % (base_slug, n)
        n += 1
    return slug

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['slug', 'name', 'description', 'tags']

    slug = forms.CharField(max_length=50, required=False)

    def clean(self):
        base_slug = self.cleaned_data['slug'] or slugify(name)
        slug = base_slug
        n = 1
        while Project.objects.filter(slug=slug).count():
            slug = '%s-%s' % (base_slug, n)
            n += 1
        self.cleaned_data['slug'] = slug
        return self.cleaned_data

class FeedForm(forms.Form):
    id = forms.IntegerField(required=False, widget=forms.HiddenInput())
    title = forms.CharField(widget=forms.widgets.TextInput(attrs={'class':'title'}))
    url = forms.URLField(widget=forms.widgets.TextInput(attrs={'class':'url'}))
FeedFormSet = formset_factory(FeedForm, can_delete=True, extra=1)

def formfield_class_callback(field):
    """ append a class with each field's name """
    ff = field.formfield()
    if ff:
        ff.widget.attrs['class'] = field.name
    return ff
LinkFormSet = inlineformset_factory(Project, Link, extra=3,
                                    formfield_callback=formfield_class_callback)
RoleFormSet = inlineformset_factory(Project, Role, extra=0, fields=['status'],
                                    can_delete=False,
                                    formfield_callback=formfield_class_callback)

class JoinProjectForm(forms.Form):
    message = forms.CharField(widget=forms.widgets.Textarea)

