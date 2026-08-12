# LangBot 终端启动入口
# 在此层级解决依赖项检查。
# LangBot/main.py

asciiart = r"""
 _                   ___      _   
| |   __ _ _ _  __ _| _ ) ___| |_ 
| |__/ _` | ' \/ _` | _ \/ _ \  _|
|____\__,_|_||_\__, |___/\___/\__|
               |___/              

⭐️开源地址: https://github.com/RockChinQ/LangBot
📖文档地址: https://docs.langbot.app
"""


import asyncio


async def main_entry(loop: asyncio.AbstractEventLoop):
    print(asciiart)

    import sys

    # 检查依赖

    from pkg.core.bootutils import deps

    missing_deps = await deps.check_deps()

    if missing_deps:
        print("以下依赖包未安装，将自动安装，请完成后重启程序：")
        for dep in missing_deps:
            print("-", dep)
        await deps.install_deps(missing_deps)
        print("已自动安装缺失的依赖包，请重启程序。")
        sys.exit(0)

    # 检查pydantic版本，如果没有 pydantic.v1，则把 pydantic 映射为 v1
    import pydantic.version
    if pydantic.version.VERSION < '2.0':
        import pydantic
        sys.modules['pydantic.v1'] = pydantic

    # 检查配置文件

    from pkg.core.bootutils import files

    generated_files = await files.generate_files()

    if generated_files:
        print("以下文件不存在，已自动生成：")
        for file in generated_files:
            print("-", file)

    from pkg.core import boot
    await boot.main(loop)


if __name__ == '__main__':
    import os
    import sys

    # 必须大于 3.10.1
    if sys.version_info < (3, 10, 1):
        print("需要 Python 3.10.1 及以上版本，当前 Python 版本为：", sys.version)
        input("按任意键退出...")
        exit(1)

    # 检查本目录是否有main.py，且包含LangBot字符串
    invalid_pwd = False

    if not os.path.exists('main.py'):
        invalid_pwd = True
    else:
        with open('main.py', 'r', encoding='utf-8') as f:
            content = f.read()
            if "LangBot/main.py" not in content:
                invalid_pwd = True
    if invalid_pwd:
        print("请在 LangBot 项目根目录下以命令形式运行此程序。")
        input("按任意键退出...")
        exit(1)

    loop = asyncio.new_event_loop()

    loop.run_until_complete(main_entry(loop))
