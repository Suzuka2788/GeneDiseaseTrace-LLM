# 本地 Skill 版本管理

唯一维护源：本项目 `skills/biomed-gene-disease-evidence/`。

个人安装副本：`C:/Users/tongz/.codex/skills/biomed-gene-disease-evidence/`。

维护源已制作 **1.3.0**，在1.2.0基础上根据第一篇反馈明确背景群体发现、关系预设、宽泛类别和表头标签。实际安装状态以 `registry.json` 和管理脚本status为准。旧版本均保留历史标签；新规则不覆盖旧论文结果，也不把旧结果重新标为新版本。

1.3.0包含35个规则回归案例；本次发布检查结构、原文引用和工具行为，没有运行新的独立模型行为测试；不能把格式通过或外部试点反馈当作本次语义验证。规则变更见包内CHANGELOG，案例说明见 `references/boundary-cases.md`。

## 日常命令

以下在项目根目录执行，使用现有 Python 环境，无额外依赖：

```powershell
.\.venv\Scripts\python.exe skills/manage_skill.py status
.\.venv\Scripts\python.exe skills/manage_skill.py snapshot
.\.venv\Scripts\python.exe skills/manage_skill.py install
```

`status` 显示双方版本、内容哈希、已安装端是否与登记基线一致及 Git 状态。`snapshot` 保存双方当前包的 ZIP 和逐文件哈希。`install` 默认预览，不修改个人安装目录。

确需发布时：

1. 先检查双方差异，只编辑项目内维护源；包内容变更应递增版本，更新包内 CHANGELOG。
2. 完成格式/引用/必要行为检查后，提交并打与包版本匹配的标签：

   ```powershell
   git -C skills add -- biomed-gene-disease-evidence
   git -C skills commit -m "Update biomed evidence rules to VERSION"
   git -C skills tag -a biomed-gene-disease-evidence/vVERSION -m "Describe the changes and validation"
   ```

3. 预览安装，再明确执行：

   ```powershell
   .\.venv\Scripts\python.exe skills/manage_skill.py install
   .\.venv\Scripts\python.exe skills/manage_skill.py install --apply
   ```

4. 安装成功后再次运行status；将registry中的部署基线变化提交到本地Git。

安装保护：拒绝降级；拒绝同版本不同内容；拒绝覆盖与登记基线不一致的安装端；要求维护源包已提交且有匹配版本标签。不会提供force绕过开关。存在冲突时先归档、核对内容，协调为新版本。

安装前为双方保存快照；替换时保留旧安装目录用于恢复，失败时回滚。Windows安装目录恢复目标父目录的权限继承，避免临时目录的私有ACL阻止沙箱读取；该步骤失败也回滚。实际写入个人Skills目录仍受当前会话文件权限约束，预览成功不等于已获系统写入权限。

若发布进程使用不同账户而遇到Git所有权检查，先核对该仓库确为本维护源，再仅为该进程配置精确路径的临时safe.directory；不自动写全局信任、不使用通配符。另一模型可以提交补丁，由维护源协调后入库。

## 查看历史与恢复

```powershell
git -C skills log --oneline --decorate
git -C skills tag --list
git -C skills diff biomed-gene-disease-evidence/v1.0.0 biomed-gene-disease-evidence/v1.1.0 -- biomed-gene-disease-evidence
```

快照位置为项目 `.Resource/skill-archive/biomed-gene-disease-evidence/releases/`，每个快照含 `_snapshot.json` 的版本、来源和逐文件SHA-256。保留原有早期备份，不把备份目录放入可发现的个人Skills根目录。

查看旧规则可使用Git或解压快照到独立目录。若要把旧行为重新发布，先与用户确认后在维护源恢复相应内容，分配新的递增版本并记录回退原因；不要偷偷覆盖当前安装。不要强行覆盖更高版本或移动已有标签。

Git仓库只位于本项目的 `skills/.git/`，尚未设置远程地址，也没有上传。`registry.json`记录本机安装位置；换电脑时显式调整安装位置，不能照搬路径。
