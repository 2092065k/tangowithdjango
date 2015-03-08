from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from rango.models import Category, Page, UserProfile
from rango.forms import CategoryForm, PageForm, UserForm, UserProfileForm
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from datetime import datetime
from rango.bing_search import run_query
from rango.helpers import get_category_list

def index(request):
    category_list = Category.objects.order_by('-likes')[:5]
    top_page_list = Page.objects.order_by('-views')[:5]
    context_dict = {'categories' : category_list, 'top_pages' : top_page_list}
    
    visits = request.session.get('visits')
    if not visits:
        visits = 1
    reset_last_visit_time = False
    last_visit = request.session.get('last_visit')

    if last_visit:
        last_visit_time = datetime.strptime(last_visit[:-7], "%Y-%m-%d %H:%M:%S")
        if (datetime.now() - last_visit_time).seconds > 0:
            visits += 1
            reset_last_visit_time = True
    else:
        reset_last_visit_time = True

    if reset_last_visit_time:
        request.session['last_visit'] = str(datetime.now())
        request.session['visits'] = visits
        
    response = render(request, 'rango/index.html', context_dict)
    return response
	
def about(request):
    context_dict = {'message': "here is the about page."}
    if request.session.get('visits'):
        visits = request.session.get('visits')
    else:
        visits = 0
    context_dict['visits'] = visits
    return render(request, 'rango/about.html', context_dict)

def category(request, category_name_slug):
    context_dict = {}
    context_dict['result_list'] = None
    context_dict['query'] = None
    if request.method == 'POST':
        query = request.POST['query'].strip()
        if query:
            result_list = run_query(query)
            context_dict['result_list'] = result_list
            context_dict['query'] = query
    try:
        category = Category.objects.get(slug=category_name_slug)
        category.views = category.views + 1
        category.save()
        context_dict['category_name'] = category.name
        context_dict['category_name_slug'] = category_name_slug
        pages = Page.objects.filter(category=category).order_by('-views')
        context_dict['pages'] = pages
        context_dict['category'] = category
        
        #handling cookies to stop the user from liking a page multiple times
        clicked = request.session.get(str(category.id))
        show = True
        if clicked:
            if clicked == category.id:
                show = False
        context_dict['show'] = show
        
    except Category.DoesNotExist:
        pass
    #fixing a bug where site crashes if category is not in context dict
    if not context_dict['query']:
        try:
            default_query = category.name
        except:
            default_query = ""
        context_dict['query'] = default_query
    return render(request, 'rango/category.html', context_dict)

@login_required
def add_category(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        
        if form.is_valid():
            form.save(commit=True)
            return index(request)
        else:
            print form.errors
    else:
        form = CategoryForm()
    return render(request, 'rango/add_category.html', {'form' : form})

@login_required
def add_page(request, category_name_slug):
    try:
        cat = Category.objects.get(slug=category_name_slug)
    except Category.DoesNotExist:
        cat = None
    if request.method == 'POST':
        form = PageForm(request.POST)
        if form.is_valid():
            if cat:
                page = form.save(commit = False)
                page.category = cat
                page.views = 0
                page.save()
                return category(request, category_name_slug)
        else:
            print form.errors
    else:
        form = PageForm()
    context_dict = {'form':form, 'category' : cat}
    return render(request, 'rango/add_page.html', context_dict)
        
@login_required
def restricted(request):
    return render(request, 'rango/restricted.html', {})
    
def track_url(request):
    page_id = None
    url = '/rango/'
    if request.method == 'GET':
        if 'page_id' in request.GET:
            page_id = request.GET['page_id']
            try:
                page = Page.objects.get(id = page_id)
                page.views = page.views + 1
                page.save()
                url = page.url
            except:
                pass
                
    return redirect(url) 
    
def register_profile(request):
    registered = False
    if request.method == 'POST':
        profile_form = UserProfileForm(data = request.POST)
        
        if profile_form.is_valid():
            profile = profile_form.save(commit = False)
            profile.user = request.user
            
            if 'picture' in request.FILES:
                profile.picture = request.FILES['picture']
            
            profile.save()
            registered = True
        else:
            print profile_form.errors
    else:
        profile_form = UserProfileForm()
    return render(request, 'rango/profile_registration.html', {'profile_form' : profile_form, 'registered' : registered})

def profile(request, user_username):
    context_dict = {}
    personal_profile = False
    try:
        user = User.objects.get(username = user_username)
        userProfile = UserProfile.objects.get(user = user)
        context_dict['username'] = user.username
        context_dict['email'] = user.email
        context_dict['website'] = userProfile.website
        context_dict['website_name'] = userProfile.website[7:]
        context_dict['picture'] = userProfile.picture
        if user ==request.user:
            personal_profile = True
    except:
        pass
    context_dict['personal_profile'] = personal_profile
    return render(request, 'rango/profile.html', context_dict)
    
@login_required
def edit_profile(request):
    editing_done = False
    if request.method == 'POST':
        profile_form = UserProfileForm(data = request.POST)
         #try and catch here to fix the profiles created with default registration only
        try:
            profile = UserProfile.objects.get(user = request.user)
        except:
            profile = profile_form.save(commit = False)
            profile.user = request.user
        if profile_form.is_valid():
            profile.website = request.POST['website']
            if 'picture' in request.FILES:
                profile.picture = request.FILES['picture']
            profile.save()
            editing_done = True
    else:
        profile_form = UserProfileForm()
    return render(request, 'rango/edit_profile.html', {'profile_form' : profile_form, 'editing_done' : editing_done})    
    
def users(request):
    context_dict = {}
    try:
        users = User.objects.order_by('username')
        context_dict['users'] = users
    except:
        pass
    return render(request, 'rango/users.html', context_dict)
 
@login_required 
def like_category(request):
    cat_id = None
    if request.method == 'GET':
        cat_id = request.GET['category_id']
    
    likes = 0
    if cat_id:
        cat = Category.objects.get(id=int(cat_id))
        if cat:
            likes = cat.likes + 1
            cat.likes = likes
            cat.save()
        #a cookie to stop a user from liking a page multiple times
        liked_cat = str(cat.id)
        request.session[liked_cat] = cat.id
    return HttpResponse(likes)
    
def suggest_category(request):
    cat_list = []
    starts_with = ''
    #variable passed to the cats template to hide an unnecessary message
    hide = True
    if request.method == 'GET':
        starts_with = request.GET['suggestion']
    cat_list = get_category_list(8, starts_with)
    return render(request, 'rango/cats.html', {'cats': cat_list, 'hide': hide})
    
@login_required
def auto_add_page(request):
    cat_id = None
    url = None
    title = None
    context_dict = {}
    if request.method == 'GET':
        cat_id = request.GET['category_id']
        url = request.GET['url']
        title = request.GET['title']
        if cat_id:
            category = Category.objects.get(id=int(cat_id))
            p = Page.objects.get_or_create(category=category, title=title, url=url)

            pages = Page.objects.filter(category=category).order_by('-views')
            context_dict['pages'] = pages

    return render(request, 'rango/page_list.html', context_dict)
    