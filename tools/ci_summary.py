"""Publica los resultados de pytest en el resumen visible de GitHub Actions."""
import os
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

report=Path('build/test-results.xml')
sys.stdout.reconfigure(encoding='utf-8')

def annotation(title,text):
    def escape(value):
        return value.replace('%','%25').replace('\r','%0D').replace('\n','%0A')
    title=escape(title).replace(':','%3A').replace(',','%2C')
    print(f'::error title={title}::{escape(text)}')

summary=['## Pruebas de Windows\n']
if report.is_file():
    tree=ET.parse(report)
    cases=tree.findall('.//testcase')
    failures=[case for case in cases if case.find('failure') is not None or case.find('error') is not None]
    skipped=sum(case.find('skipped') is not None for case in cases)
    summary.append(f'{len(cases)-len(failures)-skipped} passed, {len(failures)} failed, {skipped} skipped.\n')
    for case in failures[:20]:
        failure=case.find('failure')
        if failure is None: failure=case.find('error')
        text=(failure.text or failure.get('message',''))[:6000].replace('```','~~~')
        annotation(f"{case.get('classname')}.{case.get('name')}",text)
        summary.extend([f"### {case.get('classname')}.{case.get('name')}\n",f'```text\n{text}\n```\n'])
else:
    summary.append('No se generó el informe XML; las pruebas no llegaron a completarse.\n')
    output=Path('build/pytest-output.log')
    if output.is_file():
        text=output.read_text(encoding='utf-8',errors='replace')[-12000:].replace('```','~~~')
        annotation('pytest no completó el informe',text)
        summary.append(f'```text\n{text}\n```\n')
destination=Path(os.environ.get('GITHUB_STEP_SUMMARY','.local/windows-test-summary.md'))
destination.parent.mkdir(parents=True,exist_ok=True)
with destination.open('a',encoding='utf-8') as output:
    output.write('\n'.join(summary))
