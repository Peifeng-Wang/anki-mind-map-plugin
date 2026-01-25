"""
MindMap Backup and Recovery Tool
Provides export/import functionality to ensure data safety
"""
import json
import os
from aqt import mw
from aqt.qt import QDialog, QVBoxLayout, QPushButton, QTextEdit, QHBoxLayout, QFileDialog
from aqt.utils import showInfo, tooltip

class MindMapBackupDialog(QDialog):
    def __init__(self, mw):
        super().__init__(mw)
        self.mw = mw
        self.setWindowTitle("Mind Map Backup & Recovery")
        self.resize(800, 600)
        
        # Language preference (default: English)
        self.current_lang = mw.addonManager.getConfig(__name__).get('backup_language', 'en') if mw.addonManager.getConfig(__name__) else 'en'
        
        layout = QVBoxLayout(self)
        
        # Language toggle buttons
        lang_layout = QHBoxLayout()
        self.btn_en = QPushButton("English")
        self.btn_cn = QPushButton("中文")
        self.btn_en.clicked.connect(lambda: self.switch_language('en'))
        self.btn_cn.clicked.connect(lambda: self.switch_language('cn'))
        lang_layout.addWidget(self.btn_en)
        lang_layout.addWidget(self.btn_cn)
        lang_layout.addStretch()
        layout.addLayout(lang_layout)
        
        # Info text
        self.info = QTextEdit()
        self.info.setReadOnly(True)
        self.info.setMaximumHeight(100)
        layout.addWidget(self.info)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.btn_export_all = QPushButton()
        self.btn_export_all.setStyleSheet("padding: 10px; font-size: 14px; background: #28a745; color: white;")
        self.btn_export_all.clicked.connect(self.export_all_mindmaps)
        btn_layout.addWidget(self.btn_export_all)
        
        self.btn_export_selected = QPushButton()
        self.btn_export_selected.setStyleSheet("padding: 10px; font-size: 14px; background: #007bff; color: white;")
        self.btn_export_selected.clicked.connect(self.export_selected)
        btn_layout.addWidget(self.btn_export_selected)
        
        self.btn_import = QPushButton()
        self.btn_import.setStyleSheet("padding: 10px; font-size: 14px; background: #ffc107; color: black;")
        self.btn_import.clicked.connect(self.import_mindmaps)
        btn_layout.addWidget(self.btn_import)
        
        layout.addLayout(btn_layout)
        
        # Preview area
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        layout.addWidget(self.preview)
        
        # Close button
        self.btn_close = QPushButton()
        self.btn_close.clicked.connect(self.close)
        layout.addWidget(self.btn_close)
        
        # Load localized content
        self.update_ui_text()
    
    def switch_language(self, lang):
        self.current_lang = lang
        # Save preference
        config = mw.addonManager.getConfig(__name__) or {}
        config['backup_language'] = lang
        mw.addonManager.writeConfig(__name__, config)
        self.update_ui_text()
    
    def update_ui_text(self):
        # Update button styles
        if self.current_lang == 'en':
            self.btn_en.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
            self.btn_cn.setStyleSheet("")
            texts = self.get_english_text()
        else:
            self.btn_cn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
            self.btn_en.setStyleSheet("")
            texts = self.get_chinese_text()
        
        # Apply texts
        self.info.setHtml(texts['info'])
        self.btn_export_all.setText(texts['export_all'])
        self.btn_export_selected.setText(texts['export_selected'])
        self.btn_import.setText(texts['import'])
        self.btn_close.setText(texts['close'])
        self.preview.setPlaceholderText(texts['preview_placeholder'])
    
    def get_english_text(self):
        return {
            'info': """
            <h3>Mind Map Backup Tool</h3>
            <p>👉 <b>Export All Mind Maps</b>: Export all mind maps as JSON files with HTML viewer</p>
            <p>👉 <b>Import Mind Maps</b>: Restore mind maps from JSON backup files</p>
            """,
            'export_all': "📤 Export All Mind Maps",
            'export_selected': "📋 Export Selected Mind Map",
            'import': "📥 Import Mind Maps",
            'close': "Close",
            'preview_placeholder': "Backup preview will be displayed here..."
        }
    
    def get_chinese_text(self):
        return {
            'info': """
            <h3>思维导图备份工具</h3>
            <p>👉 <b>导出所有思维导图</b>：将所有思维导图数据导出为JSON文件，即使插件失效也可恢复</p>
            <p>👉 <b>导入思维导图</b>：从JSON文件恢复思维导图数据</p>
            """,
            'export_all': "📤 导出所有思维导图",
            'export_selected': "📋 导出选定的思维导图",
            'import': "📥 导入思维导图",
            'close': "关闭",
                        'preview_placeholder': "备份预览将显示在这里..."
        }
    
    def export_all_mindmaps(self):
        """Export all mind maps to a single JSON file"""
        from .export_utils import export_all_mindmaps
        
        success, filename, viewer_path, count = export_all_mindmaps(self, self.mw)
        
        if not success:
            if count == 0:
                showInfo("没有找到思维导图数据")
            return
        
        # Show preview
        preview_text = f"""
✅ <b>导出成功！</b><br><br>
📁 JSON 文件：{filename}<br>
"""
        if viewer_path:
            preview_text += f"""📄 可视化查看器：{viewer_path}<br><br>
<b>🎯 如何查看思维导图：</b><br>
  1. 双击 <code>MindMap_Viewer.html</code> 在浏览器中打开<br>
  2. 点击"选择 JSON 备份文件"，选择上面导出的 JSON 文件<br>
  3. 即可在浏览器中查看可视化的思维导图！<br><br>
"""
        else:
            preview_text += "<br>"
        
        preview_text += f"""📊 导出了 {count} 个思维导图<br><br>
<b>💡 重要提示：</b><br>
  - JSON 文件包含所有原始数据（可用文本编辑器查看）<br>
  - HTML 查看器可离线使用，不依赖任何插件<br>
    - 两个文件都保存好，即可永久保留你的思维导图！<br>
"""
        
        self.preview.setHtml(preview_text)
        tooltip(f"成功导出 {count} 个思维导图 + 可视化查看器！")
    
    def export_selected(self):
        """Export a specific mind map"""
        try:
            from .mindmap_manager import MindMapManager
            from .export_utils import export_mindmap_to_json
            
            # Show mind map selector
            manager = MindMapManager(self.mw)
            manager.exec()
            
            nid = manager.get_selected_nid()
            if not nid:
                showInfo("请选择一个思维导图")
                return
            
            note = self.mw.col.get_note(nid)
            title = note['Title']
            
            # Use unified export function
            success, filename, viewer_path = export_mindmap_to_json(self, self.mw, nid, title)
            
            if success:
                preview_msg = f"""
✅ <b>导出成功！</b><br><br>
📁 JSON 文件：{filename}<br>
"""
                if viewer_path:
                    preview_msg += f"""📄 查看器：{viewer_path}<br><br>
<b>双击 MindMap_Viewer.html 即可在浏览器中查看！</b><br>
"""
                preview_msg += f"""
<br>
📊 思维导图：{title}<br>
"""
                self.preview.setHtml(preview_msg)
                tooltip(f"成功导出思维导图：{title}")
                    
        except Exception as e:
            showInfo(f"导出失败：{e}")
            import traceback
            traceback.print_exc()
    
    def import_mindmaps(self):
        """Import mind maps from a backup file"""
        try:
            filename, _ = QFileDialog.getOpenFileName(
                self,
                "选择备份文件",
                os.path.join(os.path.expanduser("~"), "Documents"),
                "JSON Files (*.json)"
            )
            
            if not filename:
                return
            
            with open(filename, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            # Import logic
            from .note_manager import create_new_mindmap_note, get_or_create_mindmap_model
            import uuid
            
            imported_count = 0
            
            # Handle both single and multiple mind map formats
            if "mindmaps" in backup_data:
                # Multiple mind maps format
                mindmaps = backup_data["mindmaps"]
            else:
                # Single mind map format
                mindmaps = [backup_data]
            
            for mm in mindmaps:
                try:
                    # Create new mind map note
                    title = mm.get("title", "Imported Mind Map")
                    uid = mm.get("uuid", str(uuid.uuid4()))
                    
                    # Create note
                    model = get_or_create_mindmap_model()
                    note = self.mw.col.new_note(model)
                    note['Title'] = title + " (导入)"
                    note['UUID'] = uid
                    note['AllowNewCards'] = mm.get("allow_new_cards", "1")
                    note['Data'] = json.dumps(mm.get("data", {}))
                    note['DisplayHTML'] = f"<h1>{title}</h1><p>(Imported from backup)</p>"
                    
                    self.mw.col.add_note(note, 0)
                    imported_count += 1
                    
                except Exception as e:
                    print(f"Error importing mind map {mm.get('title', 'unknown')}: {e}")
            
            self.preview.setHtml(f"""
✅ <b>导入成功！</b><br><br>
📊 导入了 {imported_count} 个思维导图<br><br>
请在 Mind Map Manager 中查看导入的思维导图。
""")
            tooltip(f"成功导入 {imported_count} 个思维导图！")
            
        except Exception as e:
            showInfo(f"导入失败：{e}")
            import traceback
            traceback.print_exc()


def show_backup_dialog():
    """Show the backup dialog"""
    dialog = MindMapBackupDialog(mw)
    dialog.exec()
