FROM pytorch/pytorch:2.6.0-cuda12.6-cudnn9-runtime

RUN pip install --root-user-action ignore --no-cache-dir chai_lab==0.6.1
ENTRYPOINT ["chai-lab"]
