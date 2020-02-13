import json
import wget
import os.path
from distutils.dir_util import mkpath
from urllib.error import HTTPError

blocktopus_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'octopus', 'blocktopus')
)

resources_dir = os.path.join(blocktopus_dir, 'resources', 'cache')
resources_dir = os.path.join(blocktopus_dir, 'resources', 'cache')
resources_json = os.path.join(blocktopus_dir, 'templates', 'template-resources.json')

if __name__ == "__main__":
    print ("Downloading third-party resources")

    try:
        os.mkdir(resources_dir)
    except FileExistsError:
        pass

    with open(resources_json) as templates_file:
        resources = {}

        for template_items in json.load(templates_file).values():
            resources.update(template_items)
        
        extra_resources = {}
        for cache_filename, resource_url in resources.items():
            split_filename = cache_filename.split('.')

            if len(split_filename) > 3 and split_filename[-2] == 'min' and split_filename[-1] in ('js', 'css'):
                base_filename = os.path.splitext(cache_filename)[0]
                base_url = os.path.splitext(resource_url)[0]

                ext = '.map'
                extra_resources[base_filename + ext] = base_url + ext

            elif split_filename[-1] == 'ttf':
                base_filename = os.path.splitext(cache_filename)[0]
                base_url = os.path.splitext(resource_url)[0]

                for ext in ('.eot', '.woff', '.woff2', '.svg'):
                    extra_resources[base_filename + ext] = base_url + ext

        def fetch_resource (url, filename, allow_fail = False):
            cache_file = os.path.join(resources_dir, filename)
            cache_file_dir = os.path.dirname(cache_file)
            mkpath(cache_file_dir)

            if os.path.isfile(cache_file):
                print(f"{filename} already downloaded")
                return

            print(f"Downloading {url}")

            try:
                downloaded_file = wget.download(
                    url = url, 
                    out = cache_file
                )
                print("\n")
            except HTTPError:
                if allow_fail:
                    print("  [Not found]")
                else:
                    raise

        for cache_filename, resource_url in resources.items():
            fetch_resource(resource_url, cache_filename)
        
        for cache_filename, resource_url in extra_resources.items():
            fetch_resource(resource_url, cache_filename, allow_fail = True)

