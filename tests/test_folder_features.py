import unittest

from src.main import app, db


class FolderFeatureTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        with app.app_context():
            db.drop_all()
            db.create_all()
        self.client = app.test_client()

    def test_folder_crud_and_note_assignment(self):
        create_folder_response = self.client.post('/api/folders', json={'name': 'Work'})
        self.assertEqual(create_folder_response.status_code, 201)
        folder = create_folder_response.get_json()
        self.assertEqual(folder['name'], 'Work')

        create_note_response = self.client.post('/api/notes', json={
            'title': 'Project plan',
            'content': 'Ship the release',
            'folder_id': folder['id']
        })
        self.assertEqual(create_note_response.status_code, 201)
        note = create_note_response.get_json()
        self.assertEqual(note['folder_id'], folder['id'])

        rename_response = self.client.put(f"/api/folders/{folder['id']}", json={'name': 'Personal'})
        self.assertEqual(rename_response.status_code, 200)
        self.assertEqual(rename_response.get_json()['name'], 'Personal')

        move_response = self.client.put(f"/api/notes/{note['id']}", json={'folder_id': None})
        self.assertEqual(move_response.status_code, 200)
        self.assertIsNone(move_response.get_json()['folder_id'])

        delete_response = self.client.delete(f"/api/folders/{folder['id']}")
        self.assertEqual(delete_response.status_code, 204)


if __name__ == '__main__':
    unittest.main()
