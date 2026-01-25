"""
Unified mind map export utility functions
Avoid duplicating export logic across multiple files
"""
import json
import os
from datetime import datetime
from aqt.qt import QFileDialog


def export_mindmap_to_json(parent_widget, mw, note_id, title=None):
    """
    Export single mind map to JSON file and copy visualization viewer
    
    Args:
        parent_widget: Parent window (for file dialog)
        mw: Anki main window
        note_id: Mind map note ID
        title: Mind map title (optional, read from note if not provided)
    
    Returns:
        tuple: (success: bool, filename: str or None, viewer_path: str or None)
    """
    try:
        # Get mind map note
        note = mw.col.get_note(note_id)
        
        if title is None:
            title = note['Title']
        
        # Get UUID field (with fallback)
        try:
            uuid_val = note['UUID']
        except KeyError:
            uuid_val = ''
        
        # Get AllowNewCards field (with fallback)
        try:
            allow_new = note['AllowNewCards']
        except KeyError:
            allow_new = '1'
        
        # Prepare export data
        backup_data = {
            "export_date": datetime.now().isoformat(),
            "title": title,
            "uuid": uuid_val,
            "data": json.loads(note['Data']) if note['Data'] else {},
            "allow_new_cards": allow_new
        }
        
        # Generate safe filename
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '_', '-'))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"mindmap_{safe_title}_{timestamp}.json"
        
        # Show save dialog
        filename, _ = QFileDialog.getSaveFileName(
            parent_widget,
            f"Export Mind Map: {title}",
            os.path.join(os.path.expanduser("~"), "Documents", default_filename),
            "JSON Files (*.json)"
        )
        
        if not filename:
            return False, None, None
        
        # Save JSON file
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
        
        # Copy standalone viewer
        viewer_path = None
        try:
            addon_dir = os.path.dirname(__file__)
            viewer_source = os.path.join(addon_dir, "web", "standalone_viewer.html")
            export_dir = os.path.dirname(filename)
            viewer_dest = os.path.join(export_dir, "MindMap_Viewer.html")
            
            if os.path.exists(viewer_source):
                import shutil
                shutil.copy2(viewer_source, viewer_dest)
                viewer_path = viewer_dest
        except Exception as e:
            print(f"Failed to copy viewer: {e}")
        
        return True, filename, viewer_path
        
    except Exception as e:
        print(f"Export failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None, None


def export_all_mindmaps(parent_widget, mw):
    """
    Export all mind maps to single JSON file
    
    Args:
        parent_widget: Parent window (for file dialog)
        mw: Anki main window
    
    Returns:
        tuple: (success: bool, filename: str or None, viewer_path: str or None, count: int)
    """
    try:
        # Find all mind map notes
        ids = mw.col.find_notes('"note:MindMap Master"')
        
        if not ids:
            return False, None, None, 0
        
        # Get Anki version
        try:
            anki_ver = str(mw.col.version())
        except:
            anki_ver = "unknown"
        
        # Collect all mind map data
        backup_data = {
            "export_date": datetime.now().isoformat(),
            "anki_version": anki_ver,
            "mindmaps": []
        }
        
        for nid in ids:
            note = mw.col.get_note(nid)
            
            # Get fields (with fallback)
            try:
                uuid_val = note['UUID']
            except KeyError:
                uuid_val = ''
            
            try:
                allow_new = note['AllowNewCards']
            except KeyError:
                allow_new = '1'
            
            mindmap_info = {
                "title": note['Title'],
                "uuid": uuid_val,
                "data": json.loads(note['Data']) if note['Data'] else {},
                "allow_new_cards": allow_new,
                "note_id": nid
            }
            backup_data["mindmaps"].append(mindmap_info)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"anki_mindmaps_backup_{timestamp}.json"
        
        # Show save dialog
        filename, _ = QFileDialog.getSaveFileName(
            parent_widget,
            "Save Mind Maps Backup",
            os.path.join(os.path.expanduser("~"), "Documents", default_filename),
            "JSON Files (*.json)"
        )
        
        if not filename:
            return False, None, None, 0
        
        # Save JSON file
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
        
        # Copy standalone viewer
        viewer_path = None
        try:
            addon_dir = os.path.dirname(__file__)
            viewer_source = os.path.join(addon_dir, "web", "standalone_viewer.html")
            export_dir = os.path.dirname(filename)
            viewer_dest = os.path.join(export_dir, "MindMap_Viewer.html")
            
            if os.path.exists(viewer_source):
                import shutil
                shutil.copy2(viewer_source, viewer_dest)
                viewer_path = viewer_dest
        except Exception as e:
            print(f"Failed to copy viewer: {e}")
        
        return True, filename, viewer_path, len(ids)
        
    except Exception as e:
        print(f"Export all failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None, None, 0
