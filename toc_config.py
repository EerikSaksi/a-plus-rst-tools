from sphinx import addnodes
from docutils import nodes
import yaml_writer


def prepare(app):
    ''' Prepares environment for configuration values. '''
    yaml_writer.create_directory(app)
    app.env.aplus = {}
    app.env.aplus['exercises'] = {}


def store_exercise(env, docname, data_dict):
    ''' Stores exercise data for higher level configuration. '''
    if not docname in env.aplus['exercises']:
        env.aplus['exercises'][docname] = []
    env.aplus['exercises'][docname].append(data_dict)


def write(app, exception):
    ''' Writes the table of contents level configuration. '''
    if exception:
        return

    course_open = app.config.course_open_date
    course_close = app.config.course_close_date

    modules = []
    category_keys = []

    def traverse_tocs(doc):
        names = []
        for toc in doc.traverse(addnodes.toctree):
            for _,docname in toc.get('entries', []):
                names.append(docname)
        return [(name,app.env.get_doctree(name)) for name in names]

    def first_title(doc):
        titles = doc.traverse(nodes.title)
        return titles[0].astext() if titles else 'Unnamed'

    # Recursive chapter parsing.
    def parse_chapter(docname, doc, parent):

        if docname in app.env.aplus['exercises']:
            for config in app.env.aplus['exercises'][docname]:
                exercise = {
                    'key': config['key'],
                    'config': config['key'] + '.yaml',
                    'max_submissions': config['max_submissions'],
                    'max_points': config['max_points'],
                    'allow_assistant_grading': True,
                    'status': 'unlisted',
                    'category': config['category'],
                }
                parent.append(exercise)
                if not config['category'] in category_keys:
                    category_keys.append(config['category'])

        for name,child in traverse_tocs(doc):
            chapter = {
                'key': name.split('/')[-1],
                'name': first_title(child),
                'static_content': name + '.html',
                'category': 'chapter',
                'children': [],
            }
            parent.append(chapter)
            if not 'chapter' in category_keys:
                category_keys.append('chapter')
            parse_chapter(name, child, chapter['children'])

    # Traverse the documents using toctree directives.
    root = app.env.get_doctree(app.config.master_doc)
    for docname,doc in traverse_tocs(root):
        title = first_title(doc)
        # regexp to match: title (dl)
        module = {
            'key': docname.split('/')[0],
            'name': title,
            'open': course_open,
            'close': course_close, # TODO from title
            'children': [],
        }
        modules.append(module)
        parse_chapter(docname, doc, module['children'])

    # Create categories.
    categories = {key: {'name': key} for key in category_keys}

    # Get relative out dir.
    i = 0
    while i < len(app.outdir) and i < len(app.confdir) and app.outdir[i] == app.confdir[i]:
        i += 1
    if app.outdir[i] == '/':
        i += 1
    outdir = app.outdir[i:]

    # Write the configuration index.
    yaml_writer.write(
        yaml_writer.file_path(app.env, 'index'),
        {
            'static_dir': outdir,
            'start': course_open,
            'end': course_close,
            'modules': modules,
            'categories': categories,
        }
    )
