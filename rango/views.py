from django.contrib.auth import logout, authenticate, login
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.shortcuts import redirect
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from rango.models import Category, Page, UserProfile
from rango.forms import CategoryForm, PageForm, UserProfileForm, UserForm
from datetime import datetime
from rango.webhose_search import run_query
from registration.backends.simple.views import RegistrationView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
import json
import urllib.parse  # Py3
import urllib.request  # Py3


#
# def index(request):
#     context_dict = {'boldmessage': "Crunchy,creamy, cookie, candy, cupcake!"}
#     return render(request, 'rango/index.html', context=context_dict)

def get_server_side_cookie(request, cookie, default_val=None):
    val = request.session.get(cookie)
    if not val:
        val = default_val
    return val


def visitor_cookie_handler(request):
    # Get the number of visits to the site.
    # We use the COOKIES.get() function to obtain the visits cookie.
    # If the cookie exists, the value returned is casted to an integer.
    # If the cookie doesn't exist, then the default value of 1 is used.
    visits = int(get_server_side_cookie(request, 'visits', '1'))

    last_visit_cookie = get_server_side_cookie(request, 'last_visit', str(datetime.now()))

    last_visit_time = datetime.strptime(last_visit_cookie[:-7], "%Y-%m-%d %H:%M:%S")
    # last_visit_time = datetime.now()
    # If it's been more than a day since the last visit...
    if (datetime.now() - last_visit_time).seconds > 0:
        visits = visits + 1
        # update the last visit cookie now that we have updated the count
        request.session['last_visit'] = str(datetime.now())
    else:
        visits = 1
        # set the last visit cookie
        request.session['last_visit'] = last_visit_cookie
    # update/set the visits cookie
    request.session['visits'] = visits


def index(request):
    # context_dict = {'boldmessage': "Crunchie, creamy, cookie, candy, cupcake!"}
    request.session.set_test_cookie()
    category_list = Category.objects.order_by('-likes')[:5]

    page_list = Page.objects.order_by('-views')[:5]
    context_dict = {'categories': category_list, 'pages': page_list}

    visitor_cookie_handler(request)
    context_dict['visits'] = request.session['visits']

    print(request.session['visits'])
    response = render(request, 'rango/index.html', context=context_dict)

    return response


def about(request):
    if request.session.test_cookie_worked():
        print("TEST COOKIE WORKED")
        request.session.delete_test_cookie()
    return render(request, 'rango/about.html', {})


def show_category(request, category_name_slug):
    # Create a context dictionary which we can pass
    # to the template rendering engine.
    context_dict = {}

    try:
        # Can we find a category name slug with the given name?
        # If we can't, the .get() method raises a DoesNotExist exception.
        # So the .get() method returns one model instance or raises an exception.
        category = Category.objects.get(slug=category_name_slug)
        # Retrieve all of the associated pages.
        # Note that filter() returns a list of page objects or an empty list
        pages = Page.objects.filter(category=category)

        # Adds our results list to the template context under name pages.
        context_dict['pages'] = pages
        # We also add the category object from
        # the database to the context dictionary.
        # We'll use this in the template to verify that the category exists.
        context_dict['category'] = category

        # We get here if we didn't find the specified category.
        # Don't do anything -
        # the template will display the "no category" message for us.
    except Category.DoesNotExist:
        context_dict['category'] = None
        context_dict['pages'] = None

    # Go render the response and return it to the client.
    return render(request, 'rango/category.html', context_dict)


def add_category(request):
    form = CategoryForm()

    if request.method == 'POST':
        form = CategoryForm(request.POST)

        if form.is_valid():
            form.save(commit=True)

            return index(request)
        else:
            print(form.errors)

    return render(request, 'rango/add_category.html', {'form': form})


def add_page(request, category_name_slug):
    try:
        category = Category.objects.get(slug=category_name_slug)
    except Category.DoesNotExist:
        category = None

    form = PageForm()
    if request.method == 'POST':
        form = PageForm(request.POST)
        if form.is_valid():
            if category:
                page = form.save(commit=False)
                page.category = category
                page.views = 0
                page.save()
                # probably better to use a redirect here.
            return show_category(request, category_name_slug)
        else:
            print(form.errors)

    context_dict = {'form': form, 'category': category}

    return render(request, 'rango/add_page.html', context_dict)


def register(request):
    # Initial bool flag
    registered = False

    #  Check Http POST before processing
    if request.method == "POST":
        user_form = UserForm(data=request.POST)
        profile_form = UserProfileForm(data=request.POST)

        # Verify forms for user and profile form are valid
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()

            # Set password Hash using set_password method
            user.set_password(user.password)
            user.save()

            # Update UserProfile instance
            profile = profile_form.save(commit=False)
            profile.user = user

            # Check if picture file included
            if 'picture' in request.FILES:
                profile.picture = request.FILES['picture']

            # Save finally
            profile.save()
            registered = True

        else:
            print(user_form.errors, profile_form.errors)


    else:
        # Not HTTP POST so present the blank form ready for input - Initial Get request to the page
        user_form = UserForm()
        profile_form = UserProfileForm()

    # Return Render the form - Depending on Context
    return render(request, 'rango/register.html', {'user_form': user_form, 'profile_form': profile_form,
                                                   'registered': registered})


def user_login(request):
    # If post get info
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(username=username, password=password)

        if user:
            if user.is_active:
                login(request, user)
                return HttpResponseRedirect(reverse('index'))
            else:
                return HttpResponse("Your Rango Account is disabled.")
        else:
            # Bad login Scenario
            print('Invalid login details: {0}, {1}'.format(username, password))
            return HttpResponse("Invalid Login Details Provided")
    else:
        return render(request, 'rango/login.html', {})


class RangoRegistrationView(RegistrationView):
    def get_success_url(self, user):
        return reverse('register_profile')


@login_required
def restricted(request):
    return render(request, 'rango/restricted.html', {})

def search(request):
    result_list = []
    if request.method == 'POST':
        query = request.POST['query'].strip()
        if query:
             # Run our Webhose function to get the results list!
             result_list = run_query(query)
    return render(request, 'rango/search.html', {'result_list': result_list})

@login_required
def user_logout(request):
    logout(request)
    return HttpResponseRedirect(reverse('index'))


def track_url(request):
    page_id = None
    if request.method == 'GET':
        if 'page_id' in request.GET:
            page_id = request.GET['page_id']
    if page_id:
        try:
            page = Page.objects.get(id=page_id)
            page.views = page.views + 1
            page.save()
            return redirect(page.url)
        except:
            return HttpResponse("Page id {0} not found".format(page_id))
    print("No page_id in get string")
    return redirect(reverse('index'))


@login_required
def profile(request, username):
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return redirect('index')

    userprofile = UserProfile.objects.get_or_create(user=user)[0]
    form = UserProfileForm({'website': userprofile.website, 'picture': userprofile.picture})

    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=userprofile)
        if form.is_valid():
            form.save(commit=True)
            return redirect('profile', user.username)
        else:
            print(form.errors)

    return render(request, 'rango/profile.html', {'userprofile': userprofile, 'selecteduser': user, 'form': form})

@login_required
def list_profiles(request):
#    user_list = User.objects.all()
    userprofile_list = UserProfile.objects.all()
    return render(request, 'rango/list_profiles.html', { 'userprofile_list' : userprofile_list})


@login_required
def register_profile(request):
    form = UserProfileForm()
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES)
        if form.is_valid():
            user_profile = form.save(commit=False)
            user_profile.user = request.user
            user_profile.save()

            return redirect('index')
        else:
            print(form.errors)

    context_dict = {'form': form}

    return render(request, 'rango/profile_registration.html', context_dict)


def read_webhose_key():
    """
#     Reads the Webhose API key from a file called 'search.key'.
#     Returns either None (no key found), or a string representing the key.
#     Remember: put search.key in your .gitignore file to avoid committing it!
#     """
    #     # See Python Anti-Patterns - it's an awesome resource!
    #     # Here we are using "with" when opening files.
    #     http://docs.quantifiedcode.com/python-anti-patterns/maintainability/
    webhose_api_key = None
    #
    try:
        with open('search.key', 'r') as f:
            webhose_api_key = f.readline().strip()
    except:
        raise IOError('search.key file not found')

    return webhose_api_key


def run_query(search_terms, size=10):
    """
#     Given a string containing search terms (query), and a number of results to return (default of 10),
#     returns a list of results from the Webhose API, with each result consisting of a title, link and summary.
#     """
    webhose_api_key = read_webhose_key()
    #
    if not webhose_api_key:
        raise KeyError('Webhose key not found')
    #
    # What's the base URL for the Webhose API?
    root_url = 'http://webhose.io/search'
    #
    #     # Format the query string - escape special characters.
    query_string = urllib.parse.quote(search_terms)  # Py3
    #
    #     # Use string formatting to construct the complete API URL.
    search_url = '{root_url}?token={key}&format=json&q={query}&sort=relevancy&size={size}'.format(
        root_url=root_url,
        key=webhose_api_key,
        query=query_string,
        size=size)
    results = []

    try:
        # Connect to the Webhose API, and convert the response to a Python dictionary.
        response = urllib.request.urlopen(search_url).read().decode('utf-8')  # Py3 (library, decode)
        json_response = json.loads(response)

        # Loop through the posts, appendng each to the results list as a dictionary.
        for post in json_response['posts']:
            results.append({'title': post['title'],
                            'link': post['url'],
                            'summary': post['text'][:200]})
    except:
        print("Error when querying the Webhose API")

    # Return the list of results to the calling function.
    return results
