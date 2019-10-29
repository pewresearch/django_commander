from future import standard_library

standard_library.install_aliases()

from django.contrib.auth.decorators import login_required


def login(request):

    pass


@login_required
def logout(request):

    pass
