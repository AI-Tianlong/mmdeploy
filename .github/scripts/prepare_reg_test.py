# Copyright (c) OpenMMLab. All rights reserved.

import argparse
import os
import os.path as osp
import shutil
import subprocess
import tempfile

from packaging import version

REPO_NAMES = dict(
    mmcls='mmclassification',
    mmdet='mmdetection',
    mmseg='mmsegmentation',
    mmdet3d='mmdetection3d',
    mmedit='mmediting',
    mmocr='mmocr',
    mmpose='mmpose',
    mmrotate='mmrotate',
    mmaction='mmaction2',
    mmyolo='mmyolo')

MMDEPLOY_DIR = osp.abspath(osp.join(osp.dirname(__file__), '..', '..'))


def run_cmd(cmd_lines, log_path=None, raise_error=True):
    """
    Args:
        cmd_lines: (list[str]): A command in multiple line style.
        log_path (str): Path to log file.
        raise_error (bool): Whether to raise error when running cmd fails.
    """
    import platform
    system = platform.system().lower()

    if system == 'windows':
        sep = r'`'
    else:  # 'Linux', 'Darwin'
        sep = '\\'
    cmd_for_run = ' '.join(cmd_lines)
    cmd_for_log = f' {sep}\n'.join(cmd_lines) + '\n'
    if log_path is None:
        log_path = tempfile.NamedTemporaryFile(suffix='.log').name
    log_dir, _ = osp.split(log_path)
    os.makedirs(log_dir, exist_ok=True)
    print(100 * '-')
    print(f'Start running cmd\n{cmd_for_log}')
    print(f'Logging log to \n{log_path}')

    with open(log_path, 'a', encoding='utf-8') as file_handler:
        # write cmd
        file_handler.write(f'Command:\n{cmd_for_log}\n')
        file_handler.flush()
        process_res = subprocess.Popen(
            cmd_for_run,
            cwd=MMDEPLOY_DIR,
            shell=True,
            stdout=file_handler,
            stderr=file_handler)
        process_res.wait()
        return_code = process_res.returncode
    with open(log_path, 'r') as f:
        content = f.read()
        print(f'Log message:\n{content}')
    if return_code != 0:
        print(f'Got shell return code={return_code}')
        if raise_error:
            raise RuntimeError(f'Failed to run cmd:\n{cmd_for_run}')


def prepare_codebases(codebases):
    run_cmd(['python -m mim install "mmcv>=2.0.0"'])
    for codebase in codebases:
        full_name = REPO_NAMES[codebase]
        target_dir = os.path.join(MMDEPLOY_DIR, '..', full_name)
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
        branch = 'main'
        if codebase == 'mmcls':
            branch = 'mmcls-1.x'
        elif codebase == 'mmrotate':
            branch = 'dev-1.x'
        elif codebase == 'mmedit':
            branch = 'v1.0.0rc7'
        run_cmd([
            'git clone --depth 1 ', f'-b {branch} '
            f'https://github.com/open-mmlab/{full_name}.git '
            f'{target_dir} '
        ])
        run_cmd([
            'python -m pip install ',
            f'-r {target_dir}/requirements.txt ',
            f'-r {target_dir}/requirements/mminstall.txt ',
        ])
        run_cmd([f'python -m pip install {target_dir}'])
        if codebase == 'mmyolo':
            cmd = [
                f'cp -r {target_dir}/configs/deploy ',
                f'{MMDEPLOY_DIR}/configs/mmyolo '
            ]
            run_cmd(cmd)
            cmd = [
                f'cp {target_dir}/tests/regression/mmyolo.yml ',
                f'{MMDEPLOY_DIR}/tests/regression/mmyolo.yml '
            ]
            run_cmd(cmd)


def install_torch(torch_version):
    cuda_version = os.environ.get('CUDA_VERSION', '11.3')
    cuda_int = ''.join(cuda_version.split('.')[:2])
    if version.parse(torch_version) < version.parse('1.10.0'):
        cuda_int = '111'
    is_torch_v2 = version.parse(torch_version) >= version.parse('2.0.0')
    if is_torch_v2:
        tv_version = '0.15.1'
        cuda_int = '117'
    else:
        ver = version.parse(torch_version)
        tv_version = f'0.{ver.minor+1}.{ver.micro}'
    if is_torch_v2:
        cmd = [
            f'python -m pip install torch=={torch_version} ',
            f'torchvision=={tv_version} '
        ]
    else:
        url = f'https://download.pytorch.org/whl/cu{cuda_int}'
        cmd = [
            'python -m pip install ', f'torch=={torch_version}+cu{cuda_int} ',
            f'torchvision=={tv_version}+cu{cuda_int} ', f'-f {url}'
        ]
    run_cmd(cmd)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--torch-version', type=str, help='Torch version')
    parser.add_argument(
        '--codebases', type=str, nargs='+', help='Codebase names')
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    print(args)
    assert len(args.codebases) > 0, 'at least input one codebases'
    install_torch(args.torch_version)
    prepare_codebases(args.codebases)


if __name__ == '__main__':
    main()
