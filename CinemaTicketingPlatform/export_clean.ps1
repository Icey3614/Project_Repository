# 生成干净的源码压缩包（仅包含 git 跟踪的文件），便于安全转发/上传。
# 用法：在项目根目录执行 .\export_clean.ps1

$ErrorActionPreference = "Stop"

$archive = "CinemaTicketingPlatform-source.zip"
if (Test-Path $archive) {
    Write-Host "已存在 $archive，请先删除或改名。" -ForegroundColor Yellow
    exit 1
}

git archive --format=zip -o $archive HEAD
Write-Host "已生成 $archive（仅含版本控制文件，无 .env、无构建产物、无依赖目录）" -ForegroundColor Green
