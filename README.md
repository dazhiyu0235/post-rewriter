# WordPress文章更新器

这是一个用于更新WordPress网站文章的工具，可以删除文章中的文字内容，只保留图片。

## 功能特点

- 🔗 支持WordPress XML-RPC和REST API连接
- 🖼️ 智能识别和保留文章中的图片
- 📝 删除所有文字内容，保持页面结构
- 🔄 支持单篇文章和批量更新
- 🧪 提供试运行模式，预览处理结果
- 📊 详细的处理日志和统计信息
- 🛡️ 安全的认证机制

## 安装要求

- Python 3.7+
- WordPress网站（启用XML-RPC或REST API）

## 安装步骤

1. **克隆或下载项目**
   ```bash
   git clone <repository-url>
   cd post-rewriter
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置WordPress连接**
   ```bash
   # 复制配置示例文件
   cp env_example.txt .env
   
   # 编辑 .env 文件，填写您的WordPress配置
   nano .env
   ```

## 配置说明

在 `.env` 文件中配置以下参数：

```env
# WordPress网站URL
WORDPRESS_URL=https://your-wordpress-site.com

# WordPress用户名
WORDPRESS_USERNAME=your_username

# WordPress应用密码
WORDPRESS_APP_PASSWORD=your_app_password
```

### WordPress设置要求

1. **启用XML-RPC**（推荐）
   - 在WordPress管理后台，确保XML-RPC功能已启用
   - 路径：设置 > 讨论 > XML-RPC

2. **或启用REST API**
   - 确保WordPress REST API功能正常
   - 路径：设置 > 固定链接（选择非默认设置）

3. **生成应用密码**
   - 登录WordPress管理后台
   - 进入：用户 > 个人资料
   - 滚动到页面底部的"应用密码"部分
   - 输入应用名称（如"文章更新器"）
   - 点击"添加新的应用密码"
   - 复制生成的密码到 `.env` 文件

4. **用户权限**
   - 确保配置的用户有编辑文章的权限
   - 必须使用应用密码进行认证

## 使用方法

### 1. 更新单篇文章（试运行）

python3 main.py --file urls.txt --dry-run

```bash
python main.py --url "https://your-site.com/post/123" --dry-run
```

### 2. 更新单篇文章（实际更新）

```bash
python main.py --url "https://your-site.com/post/123"
```

### 3. 批量更新文章

首先创建包含URL列表的文件 `urls.txt`：
```
https://your-site.com/post/1
https://your-site.com/post/2
https://your-site.com/post/3
```

然后运行批量更新：
```bash
python main.py --file urls.txt --dry-run
```

### 4. 获取文章信息

```bash
python main.py --url "https://your-site.com/post/123" --info
```

### 5. 显示详细日志

```bash
python main.py --url "https://your-site.com/post/123" --verbose
```

## 命令行参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--url` | 要更新的文章URL | `--url "https://example.com/post/123"` |
| `--file` | 包含多个URL的文件 | `--file urls.txt` |
| `--dry-run` | 试运行模式，不实际更新 | `--dry-run` |
| `--info` | 只获取文章信息 | `--info` |
| `--verbose` | 显示详细日志 | `--verbose` |

## 工作原理

1. **连接WordPress**：使用XML-RPC或REST API连接到WordPress网站
2. **获取文章内容**：根据URL获取指定文章的HTML内容
3. **解析HTML**：使用BeautifulSoup解析HTML结构
4. **保留图片**：识别并保留所有`<img>`、`<figure>`、`<picture>`等图片相关标签
5. **删除文字**：删除所有文字内容，清理空容器
6. **更新文章**：将处理后的内容更新到WordPress

## 支持的图片格式

- `<img>` 标签
- `<figure>` 和 `<figcaption>` 组合
- `<picture>` 和 `<source>` 组合
- 响应式图片

## 安全注意事项

1. **使用应用密码**：必须在WordPress中生成应用密码进行认证
2. **限制权限**：为更新器创建专门的用户账户，只赋予编辑文章权限
3. **备份数据**：在批量更新前，建议备份WordPress数据库
4. **试运行测试**：首次使用建议使用 `--dry-run` 参数测试

## 故障排除

### 连接失败
- 检查WordPress URL是否正确
- 确认XML-RPC或REST API已启用
- 验证用户名和应用密码是否正确

### 权限错误
- 确认用户有编辑文章的权限
- 检查WordPress用户角色设置

### 文章未找到
- 确认文章URL格式正确
- 检查文章是否已发布
- 验证文章ID或slug是否正确

## 日志文件

程序运行时会生成 `wordpress_updater.log` 日志文件，包含详细的处理信息。

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request来改进这个工具。

## 免责声明

使用此工具前请务必备份您的WordPress数据。作者不对使用此工具造成的任何数据丢失负责。
