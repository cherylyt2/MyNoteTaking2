from flask import Blueprint, jsonify, request

from src.models.folder import Folder
from src.models.note import Note, db

folder_bp = Blueprint('folder', __name__)


@folder_bp.route('/folders', methods=['GET'])
def get_folders():
    folders = Folder.query.order_by(Folder.name.asc()).all()
    return jsonify([folder.to_dict() for folder in folders])


@folder_bp.route('/folders', methods=['POST'])
def create_folder():
    data = request.json or {}
    name = (data.get('name') or '').strip()

    if not name:
        return jsonify({'error': 'Folder name is required'}), 400

    if Folder.query.filter_by(name=name).first():
        return jsonify({'error': 'A folder with that name already exists'}), 409

    folder = Folder(name=name)
    db.session.add(folder)
    db.session.commit()
    return jsonify(folder.to_dict()), 201


@folder_bp.route('/folders/<int:folder_id>', methods=['GET'])
def get_folder(folder_id):
    folder = Folder.query.get_or_404(folder_id)
    return jsonify(folder.to_dict())


@folder_bp.route('/folders/<int:folder_id>', methods=['PUT'])
def update_folder(folder_id):
    folder = Folder.query.get_or_404(folder_id)
    data = request.json or {}
    new_name = (data.get('name') or '').strip()

    if not new_name:
        return jsonify({'error': 'Folder name is required'}), 400

    if Folder.query.filter(Folder.id != folder_id, Folder.name == new_name).first():
        return jsonify({'error': 'A folder with that name already exists'}), 409

    folder.name = new_name
    db.session.commit()
    return jsonify(folder.to_dict())


@folder_bp.route('/folders/<int:folder_id>', methods=['DELETE'])
def delete_folder(folder_id):
    folder = Folder.query.get_or_404(folder_id)
    Note.query.filter_by(folder_id=folder.id).update({'folder_id': None})
    db.session.delete(folder)
    db.session.commit()
    return '', 204


@folder_bp.route('/folders/<int:folder_id>/notes', methods=['GET'])
def get_folder_notes(folder_id):
    folder = Folder.query.get_or_404(folder_id)
    notes = folder.notes.order_by(Note.updated_at.desc()).all()
    return jsonify([note.to_dict() for note in notes])
