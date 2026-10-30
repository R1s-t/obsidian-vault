Python历史
基础代码库
大量第三方库
命令行窗口
打开"powershell"
打开：python
`>>>`表示在python交互环境
`exit()`退出
安装时记得勾选`Add Python 3.x to PATH`

`.py`文件

解释器

| CPython | IPython  | PyPy              | Jython | IronPython |
| ------- | -------- | ----------------- | ------ | ---------- |
| `>>>`   | `In[序号]` | 速度快，注意与CPython不同点 | Java   | .Net       |
```

假如你想要将Python程序编译为dll，或so，用来给其它程序使用，那么，你需要用Cython。 假如你想要将Python程序编译为可脱离解释器的可直接执行的exe，那么，你需要用nuitka。 总而言之，Python编译部署的选择很多，很自由。
```

| 命令行模式     | Python交互模式 |
| --------- | ---------- |
| `PS C:\>` | `>>>`      |
打开交互模式：`python` `Python (command line)`
退出：`exit()`
打印函数`print()`，用`''`或`""`，不能混用，内部文本为字符串
`python hello.py`运行`.py`文件，执行一个`.py`文件只能在命令行模式下运行
==要事先切换到所在目录下==，如`cd work`此时`.py`文件存储在`work`中，`cd`是切换命令
也可用绝对路径`cd **\**\**`
Windows中，切换盘需输入如`D:`，再用`cd`命令切换文件

>Python交互环境，把每一行Python代码自动打印
>命令行模式运行`.py`文件不会，要用`print()`

Python交互模式代码是输入一行，执行一行，主要为了调试代码，不是正式运行Python的环境
命令行模式一次性运行`.py`文件内的所有代码
`SyntaxError`表示输入的代码有语法错误
`invalid character`表示有无法识别的字符
Window上无法像`.exe`直接运行`.py`文件