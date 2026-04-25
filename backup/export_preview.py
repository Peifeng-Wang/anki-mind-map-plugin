"""Export result preview formatting for the backup tool."""
import html


def _escape(value):
    return html.escape(str(value), quote=True)


def _format_export_all_preview(filename, viewer_path, count):
    viewer_line = ""
    viewer_help = ""
    if viewer_path:
        viewer_line = f"查看器：{_escape(viewer_path)}<br><br>"
        viewer_help = """
            <b>如何查看思维导图：</b><br>
            1. 双击 <code>MindMap_Viewer.html</code> 在浏览器中打开。<br>
            2. 点击“选择 JSON 备份文件”，选择刚导出的 JSON 文件。<br>
            3. 即可在浏览器中查看可视化思维导图。<br><br>
        """

    return f"""
        <b>导出成功！</b><br><br>
        JSON 文件：{_escape(filename)}<br>
        {viewer_line}
        {viewer_help}
        导出了 {count} 个思维导图。<br><br>
        <b>重要提示：</b><br>
        - JSON 文件包含所有原始数据。<br>
        - HTML 查看器可离线使用，不依赖 Anki 或 插件。<br>
    """


def _format_export_selected_preview(filename, viewer_path, title):
    viewer_line = ""
    if viewer_path:
        viewer_line = f"""
            查看器：{_escape(viewer_path)}<br><br>
            <b>双击 MindMap_Viewer.html 即可在浏览器中查看。</b><br>
        """

    return f"""
        <b>导出成功！</b><br><br>
        JSON 文件：{_escape(filename)}<br>
        {viewer_line}
        <br>
        思维导图：{_escape(title)}<br>
    """
