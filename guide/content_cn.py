def get_chinese_sidebar():
    return """
    <h2>目录导航</h2>
    <a href="#quick-start" class="nav-link">&#9889; 快速开始</a>
    <a href="#setup-sync" class="nav-link">&#9729; 首次同步</a>
    <a href="#operations" class="nav-link">&#9733; 基础操作</a>
    <a href="#card-linking" class="nav-link">&#8644; 卡片关联</a>
    <a href="#config" class="nav-link">&#9881; 插件配置</a>
    <a href="#advanced" class="nav-link">&#9632; 高级功能</a>
    <a href="#backup" class="nav-link">&#9851; 备份恢复</a>
    """


def get_chinese_body():
    return """
    <h1>&#9733; 思维导图插件使用指南</h1>
    <div id="quick-start" class="feature">
        <h2 style="margin-top:0;">&#9889; 快速开始流程</h2>
        <ol>
            <li><strong>创建导图：</strong>点击 <code>工具 &rarr; Mind Map &rarr; Mind Map Manager</code>，再点击 <strong>New</strong>。</li>
            <li><strong>关联卡片：</strong>在添加窗口或浏览器中点击工具栏 <strong>MM</strong> 按钮，选择目标导图。</li>
            <li><strong>编辑内容：</strong>卡片正面字段的第一行会同步为导图节点文字。</li>
            <li><strong>刷新查看：</strong>回到导图编辑器按 <strong>F5</strong>。</li>
            <li><strong>双向跳转：</strong>导图中右键节点可跳到卡片；复习时点击右上角徽章可回到导图节点。</li>
        </ol>
        <div class="tip"><strong>提示：</strong>未关联卡片的节点也可以用于结构整理、标题或头脑风暴。</div>
    </div>

    <h2 id="setup-sync">&#9729; 重要：首次同步设置</h2>
    <div class="warning">
        <strong>新用户必须注意</strong>
        <p>安装插件或首次使用启用/停用功能后，Anki 会检测到数据库结构变化。同步时请选择 <strong>上传到 AnkiWeb</strong>。</p>
        <ul>
            <li>这是一次性要求，用于建立自定义的 <code>MindMap Master</code> 笔记类型。</li>
            <li>之后的新增、编辑和关联操作会正常双向同步。</li>
        </ul>
    </div>

    <h2 id="operations">&#9733; 基础操作</h2>
    <table>
        <tr><th>操作</th><th>快捷键</th><th>说明</th></tr>
        <tr><td>添加子节点</td><td><span class="shortcut">Tab</span></td><td>在当前节点下创建子节点。</td></tr>
        <tr><td>添加同级节点</td><td><span class="shortcut">Enter</span></td><td>创建同级节点。</td></tr>
        <tr><td>编辑</td><td><span class="shortcut">空格</span> / 双击</td><td>编辑文字；<span class="shortcut">Shift+Enter</span> 换行。</td></tr>
        <tr><td>删除</td><td><span class="shortcut">Delete</span></td><td>删除节点及其所有子节点。</td></tr>
        <tr><td>移动</td><td>拖拽</td><td>拖动节点到新的父节点下。</td></tr>
    </table>
    <h3>复制、粘贴与撤销</h3>
    <ul>
        <li>选中节点后使用 <span class="shortcut">Ctrl+C</span> / <span class="shortcut">Ctrl+V</span> 可复制到另一个节点下。</li>
        <li>粘贴外部文本时，会自动创建包含该文本的子节点。</li>
        <li>撤销使用 <span class="shortcut">Ctrl+Z</span>；重做使用 <span class="shortcut">Ctrl+Y</span> 或 <span class="shortcut">Ctrl+Shift+Z</span>。</li>
    </ul>

    <h2 id="card-linking">&#8644; 卡片关联系统</h2>
    <div class="feature">
        <p>关联从卡片发起，能兼容不同卡片类型并保持流程简单。</p>
        <ul>
            <li><strong>导图到卡片：</strong>编辑已关联节点会更新卡片正面字段第一行。</li>
            <li><strong>卡片到导图：</strong>编辑卡片正面字段第一行会更新对应导图节点。</li>
        </ul>
    </div>
    <div class="warning"><strong>自动保存提醒：</strong>编辑已关联节点后，请等待右上角 Auto-saved 提示出现再关闭窗口。</div>

    <h2 id="config">&#9881; 插件配置</h2>
    <p>前往 <strong>工具 &rarr; 插件 &rarr; Mind Map &rarr; Config</strong> 自定义设置。</p>
    <ul>
        <li><strong>线条颜色：</strong>支持颜色名、Hex 或 RGBA。</li>
        <li><strong>背景图片：</strong>将图片放入 <code>backgrounds</code> 文件夹，并在配置中填写文件名。</li>
        <li><strong>快捷键：</strong>可配置保存、刷新、聚焦根节点和快速打开。</li>
    </ul>

    <h2 id="advanced">&#9632; 高级功能</h2>
    <ul>
        <li><strong>浮动节点：</strong>双击空白处创建独立节点，适合临时整理想法。</li>
        <li><strong>数学公式：</strong>支持标准行内和块级 MathJax 语法。</li>
        <li><strong>启用/停用：</strong>可在管理器中隐藏已完成导图，避免出现在卡片关联菜单。</li>
        <li><strong>全屏模式：</strong>点击工具栏全屏按钮进入沉浸式编辑。</li>
    </ul>

    <h2 id="backup">&#9851; 备份与恢复</h2>
    <p>使用 <strong>工具 &rarr; Mind Map &rarr; Backup &amp; Recovery</strong> 导出 JSON 备份，可附带离线 HTML 查看器，也可以稍后从 JSON 文件导入恢复。</p>

    <hr style="margin: 30px 0; border: none; border-top: 2px solid #3498db;">
    <p style="text-align: center; color: #95a5a6;"><small>Anki 思维导图插件 | 通过可视化增强学习</small></p>
    """
