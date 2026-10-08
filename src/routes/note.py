from flask import Blueprint, jsonify, request

from src.models.folder import Folder
from src.models.note import Note, db
from src.translator import llm_generate

note_bp = Blueprint('note', __name__)


@note_bp.route('/notes/translate', methods=['POST'])
def translate_note():
    data = request.get_json(silent=True) or {}
    content = data.get('content')
    target_language = data.get('target_language')

    if not isinstance(content, str) or not content.strip():
        return jsonify({'error': 'Note content is required'}), 400
    if not isinstance(target_language, str):
        return jsonify({'error': 'Target language is required'}), 400

    try:
        translation = llm_generate(content.strip(), target_language)
    except ValueError as error:
        return jsonify({'error': str(error)}), 400
    except RuntimeError as error:
        return jsonify({'error': str(error)}), 503
    except Exception as error:
        return jsonify({'error': str(error)}), 502

    return jsonify({
        'translation': translation,
        'target_language': target_language,
    })


@note_bp.route('/notes', methods=['GET'])
def get_notes():
    """Get all notes, ordered by most recently updated"""
    folder_id = request.args.get('folder_id')
    query = Note.query

    if folder_id not in (None, '', 'all'):
        query = query.filter_by(folder_id=int(folder_id))
    elif folder_id == 'all':
        query = query.order_by(Note.updated_at.desc())
    else:
        query = query.order_by(Note.updated_at.desc())

    notes = query.order_by(Note.updated_at.desc()).all()
    return jsonify([note.to_dict() for note in notes])


@note_bp.route('/notes', methods=['POST'])
def create_note():
    """Create a new note"""
    try:
        data = request.json or {}
        if 'title' not in data or 'content' not in data:
            return jsonify({'error': 'Title and content are required'}), 400

        folder_id = data.get('folder_id')
        if folder_id not in (None, ''):
            folder = Folder.query.get(int(folder_id))
            if folder is None:
                return jsonify({'error': 'Folder not found'}), 404
        else:
            folder_id = None

        note = Note(title=data['title'], content=data['content'], folder_id=folder_id)
        db.session.add(note)
        db.session.commit()
        return jsonify(note.to_dict()), 201
    except ValueError:
        return jsonify({'error': 'Folder id must be an integer'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@note_bp.route('/notes/<int:note_id>', methods=['GET'])
def get_note(note_id):
    """Get a specific note by ID"""
    note = Note.query.get_or_404(note_id)
    return jsonify(note.to_dict())


@note_bp.route('/notes/<int:note_id>', methods=['PUT'])
def update_note(note_id):
    """Update a specific note"""
    try:
        note = Note.query.get_or_404(note_id)
        data = request.json or {}

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        note.title = data.get('title', note.title)
        note.content = data.get('content', note.content)

        if 'folder_id' in data:
            folder_id = data.get('folder_id')
            if folder_id in (None, ''):
                note.folder_id = None
            else:
                folder = Folder.query.get(int(folder_id))
                if folder is None:
                    return jsonify({'error': 'Folder not found'}), 404
                note.folder_id = int(folder_id)

        db.session.commit()
        return jsonify(note.to_dict())
    except ValueError:
        return jsonify({'error': 'Folder id must be an integer'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@note_bp.route('/notes/<int:note_id>', methods=['DELETE'])
def delete_note(note_id):
    """Delete a specific note"""
    try:
        note = Note.query.get_or_404(note_id)
        db.session.delete(note)
        db.session.commit()
        return '', 204
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@note_bp.route('/notes/search', methods=['GET'])
def search_notes():
    """Search notes by title or content"""
    query = request.args.get('q', '')
    if not query:
        return jsonify([])

    notes = Note.query.filter(
        (Note.title.contains(query)) | (Note.content.contains(query))
    ).order_by(Note.updated_at.desc()).all()

    return jsonify([note.to_dict() for note in notes])

