from django.shortcuts import render


def handler404(request, exception=None):
    return render(request, 'error.html', {'code': 404}, status=404)


def handler500(request):
    return render(request, 'error.html', {'code': 500}, status=500)
