# OmegaTheLegends_platform
OmegaTheLegends Platform repository

-----------------------------------
ДЗ 1:

В kube-system перезапуск подов происходит по 3 контроллерам: Node ( kubelet ), ReplicaSet, DaemonSet.

Создал Dockerfile на основе python с web на порту 8000. ( omegathelegends/otus-web )
Создал манифест на основе созданого докерфайла с инит контейнером busybox и общей папкой emptyDir для редактирования index.html
По заданию со * , создан yaml с ENV которых не хватало длоя его запуска.
-----------------------------------
