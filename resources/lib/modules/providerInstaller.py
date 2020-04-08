import zipfile, xbmc, xbmcaddon, json, requests, os, base64
from resources.lib.common import tools
from resources.lib.modules import customProviders

# Below is the contents of the providers/__init__.py base64 encoded
# If you update this init file you will need to update this base64 as well to ensure it is deployed on the users machine
# If you change the init file without updating this it will be overwritten with the old one!!

init_contents = 'aW1wb3J0IG9zCmZyb20gcmVzb3VyY2VzLmxpYi5jb21tb24gaW1wb3J0IHRvb2xzCmZyb20gcmVzb3VyY2VzLmxpYi5tb2R1bGVzIGltcG9ydCBkYXRhYmFzZQoKZGF0YV9wYXRoID0gb3MucGF0aC5qb2luKHRvb2xzLmRhdGFQYXRoLCAncHJvdmlkZXJzJykKcHJvdmlkZXJfcGFja2FnZXMgPSBbbmFtZSBmb3IgbmFtZSBpbiBvcy5saXN0ZGlyKGRhdGFfcGF0aCkgaWYgb3MucGF0aC5pc2Rpcihvcy5wYXRoLmpvaW4oZGF0YV9wYXRoLCBuYW1lKSldCmhvc3Rlcl9zb3VyY2VzID0gW10KdG9ycmVudF9zb3VyY2VzID0gW10KCmRlZiBnZXRfcmVsZXZhbnQobGFuZ3VhZ2UpOgogICAgIyBHZXQgcmVsZXZhbnQgYW5kIGVuYWJsZWQgcHJvdmlkZXIgZW50cmllcyBmcm9tIHRoZSBkYXRhYmFzZQogICAgcHJvdmlkZXJfc3RhdHVzID0gW2kgZm9yIGkgaW4gZGF0YWJhc2UuZ2V0X3Byb3ZpZGVycygpIGlmIGlbJ2NvdW50cnknXSA9PSBsYW5ndWFnZV0KICAgIHByb3ZpZGVyX3N0YXR1cyA9IFtpIGZvciBpIGluIHByb3ZpZGVyX3N0YXR1cyBpZiBpWydzdGF0dXMnXSA9PSAnZW5hYmxlZCddCgogICAgZm9yIHBhY2thZ2UgaW4gcHJvdmlkZXJfcGFja2FnZXM6CiAgICAgICAgdHJ5OgogICAgICAgICAgICBwcm92aWRlcnNfcGF0aCA9ICdwcm92aWRlcnMuJXMuJXMnICUgKHBhY2thZ2UsIGxhbmd1YWdlKQogICAgICAgICAgICBwcm92aWRlcl9saXN0ID0gX19pbXBvcnRfXyhwcm92aWRlcnNfcGF0aCwgZnJvbWxpc3Q9WycnXSkKICAgICAgICAgICAgZm9yIGkgaW4gcHJvdmlkZXJfbGlzdC5nZXRfaG9zdGVycygpOgogICAgICAgICAgICAgICAgZm9yIHN0YXR1cyBpbiBwcm92aWRlcl9zdGF0dXM6CiAgICAgICAgICAgICAgICAgICAgaWYgaSA9PSBzdGF0dXNbJ3Byb3ZpZGVyX25hbWUnXToKICAgICAgICAgICAgICAgICAgICAgICAgaWYgcGFja2FnZSA9PSBzdGF0dXNbJ3BhY2thZ2UnXToKICAgICAgICAgICAgICAgICAgICAgICAgICAgICMgQWRkIGltcG9ydCBwYXRoIGFuZCBuYW1lIHRvIGhvc3Rlcl9wcm92aWRlcnMKICAgICAgICAgICAgICAgICAgICAgICAgICAgIGhvc3Rlcl9zb3VyY2VzLmFwcGVuZCgoJyVzLmhvc3RlcnMnICUgcHJvdmlkZXJzX3BhdGgsIGksIHBhY2thZ2UpKQoKICAgICAgICAgICAgZm9yIGkgaW4gcHJvdmlkZXJfbGlzdC5nZXRfdG9ycmVudCgpOgogICAgICAgICAgICAgICAgZm9yIHN0YXR1cyBpbiBwcm92aWRlcl9zdGF0dXM6CiAgICAgICAgICAgICAgICAgICAgaWYgaSA9PSBzdGF0dXNbJ3Byb3ZpZGVyX25hbWUnXToKICAgICAgICAgICAgICAgICAgICAgICAgaWYgcGFja2FnZSA9PSBzdGF0dXNbJ3BhY2thZ2UnXToKICAgICAgICAgICAgICAgICAgICAgICAgICAgICMgQWRkIGltcG9ydCBwYXRoIGFuZCBuYW1lIHRvIHRvcnJlbnRfcHJvdmlkZXJzCiAgICAgICAgICAgICAgICAgICAgICAgICAgICB0b3JyZW50X3NvdXJjZXMuYXBwZW5kKCgnJXMudG9ycmVudCcgJSBwcm92aWRlcnNfcGF0aCwgaSwgcGFja2FnZSkpCgogICAgICAgIGV4Y2VwdDoKICAgICAgICAgICAgaW1wb3J0IHRyYWNlYmFjawogICAgICAgICAgICB0cmFjZWJhY2sucHJpbnRfZXhjKCkKICAgICAgICAgICAgY29udGludWUKCiAgICByZXR1cm4gKHRvcnJlbnRfc291cmNlcywgaG9zdGVyX3NvdXJjZXMpCgpkZWYgZ2V0X2FsbChsYW5ndWFnZSk6CiAgICBmb3IgcGFja2FnZSBpbiBwcm92aWRlcl9wYWNrYWdlczoKICAgICAgICB0cnk6CiAgICAgICAgICAgIHByb3ZpZGVyc19wYXRoID0gJ3Byb3ZpZGVycy4lcy4lcycgJSAocGFja2FnZSwgbGFuZ3VhZ2UpCiAgICAgICAgICAgIHByb3ZpZGVyX2xpc3QgPSBfX2ltcG9ydF9fKHByb3ZpZGVyc19wYXRoLCBmcm9tbGlzdD1bJyddKQogICAgICAgICAgICBmb3IgaSBpbiBwcm92aWRlcl9saXN0LmdldF9ob3N0ZXJzKCk6CiAgICAgICAgICAgICAgICBob3N0ZXJfc291cmNlcy5hcHBlbmQoKCclcy5ob3N0ZXJzJyAlIHByb3ZpZGVyc19wYXRoLCBpLCBwYWNrYWdlKSkKCiAgICAgICAgICAgIGZvciBpIGluIHByb3ZpZGVyX2xpc3QuZ2V0X3RvcnJlbnQoKToKICAgICAgICAgICAgICAgIHRvcnJlbnRfc291cmNlcy5hcHBlbmQoKCclcy50b3JyZW50JyAlIHByb3ZpZGVyc19wYXRoLCBpLCBwYWNrYWdlKSkKCiAgICAgICAgZXhjZXB0OgogICAgICAgICAgICBpbXBvcnQgdHJhY2ViYWNrCiAgICAgICAgICAgIHRyYWNlYmFjay5wcmludF9leGMoKQogICAgICAgICAgICBjb250aW51ZQoKICAgIHJldHVybiAodG9ycmVudF9zb3VyY2VzLCBob3N0ZXJfc291cmNlcykK'

def install_zip(install_style):

    folders = ['providerModules/', 'providers/']
    deploy_init()
    if install_style == None:
        browse_download = tools.showDialog.select(tools.addonName, [tools.lang(40302), tools.lang(40303)])
        if browse_download == 0:
            zip_location = tools.fileBrowser(1, tools.lang(40304).format('Provider'), 'files', '.zip', True, False)
        elif browse_download == 1:
            zip_location = tools.showKeyboard('', '%s: %s' % (tools.addonName, tools.lang(40305)))
            zip_location.doModal()
            if zip_location.isConfirmed() and zip_location.getText() != '':
                zip_location = zip_location.getText()
            else:
                return
        else:
            return
    else:
        if install_style == '0':
            zip_location = tools.fileBrowser(1, tools.lang(40304).format('Provider'), 'files', '.zip', True, False)
        if install_style == '1':
            zip_location = tools.showKeyboard('', '%s: %s' % (tools.addonName, tools.lang(40305)))
            zip_location.doModal()
            if zip_location.isConfirmed() and zip_location.getText() != '':
                zip_location = zip_location.getText()
            else:
                return

    if zip_location == '':
        return
    if zip_location.startswith('smb'):
        tools.showDialog.ok(tools.addonName, tools.lang(40309))
        return
    if zip_location.startswith('http'):
        response = requests.get(zip_location, stream=True)
        if not response.ok:
            tools.showDialog.ok(tools.addonName, tools.lang(40310))
        else:
            pass
        try:
            import StringIO
            file = zipfile.ZipFile(StringIO.StringIO(response.content))
        except:
            #Python 3 Support
            import io
            file = zipfile.ZipFile(io.BytesIO(response.content))
    else:
        file = zipfile.ZipFile(zip_location)

    file_list = file.namelist()

    for i in file_list:
        if i.startswith('/') or '..' in i:
            raise Exception

    meta_file = None
    for i in file_list:
        if i.startswith('meta.json'):
            meta_file = i

    if meta_file is not None:
        meta = file.open(meta_file)
        meta = meta.readlines()
        meta = ''.join(meta)
        meta = meta.replace(' ', '').replace('\r','').replace('\n','')
        meta = json.loads(meta)
        requirements = ['author', 'name', 'version']
        for i in requirements:
            if i not in meta:
                malformed_output()
                return
        author = meta['author']
        version = meta['version']
        pack_name = meta['name']
    else:
        malformed_output()
        import traceback
        traceback.print_exc()
        raise Exception

    line1 = tools.colorString('{}: '.format(tools.lang(40311))) + '{} - v{}'.format(pack_name, version)
    line2 = tools.colorString('{}: '.format(tools.lang(40312))) + "%s" % author
    line3 = tools.lang(40313)
    accept = tools.showDialog.yesno("{} - {}".format(tools.addonName, tools.lang(40314)), line1, line2, line3,
                                    tools.lang(40315), tools.lang(40316))
    if accept == 0:
        return

    install_progress = tools.progressDialog
    install_progress.create(tools.addonName, '%s - %s' % (tools.lang(40317), pack_name), tools.lang(33009))
    install_progress.update(-1)
    try:
        for folder in folders:
            for zip_file in file_list:
                if zip_file.startswith(folder):
                    file.extract(zip_file, tools.dataPath)
        try:
            file.close()
            install_progress.close()
        except:
            pass
        tools.showDialog.ok(tools.addonName, '%s - %s' % (tools.lang(40318), pack_name))
    except:
        import traceback
        traceback.print_exc()
        install_progress.close()
        tools.showDialog.ok(tools.addonName, '%s - %s' % (tools.lang(40319), pack_name), tools.lang(40320))
        return

    customProviders.providers().update_known_providers()


def malformed_output():
    tools.showDialog.ok(tools.addonName, '%s - %s' % (tools.lang(40319)), tools.lang(40320))
    tools.log('Source pack is malformed, please check and correct issue in the meta file')

def deploy_init():
    folders = ['providerModules/', 'providers/']
    root_init_path = os.path.join(tools.dataPath, '__init__ .py')
    
    if not os.path.exists(tools.dataPath):
        os.makedirs(tools.dataPath)
    if not os.path.exists(root_init_path):
        open(root_init_path, 'a').close()
    for i in folders:
        folder_path = os.path.join(tools.dataPath, i)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        open(os.path.join(folder_path, '__init__.py'), 'a').close()
    provider_init = open(os.path.join(tools.dataPath, 'providers', '__init__.py'), 'w+')
    provider_init.write(base64.b64decode(init_contents))
