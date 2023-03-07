# OmegaTheLegends_platform
OmegaTheLegends Platform repository

 -----------------------------------

### ДЗ 1:

В kube-system перезапуск подов происходит по 3 контроллерам: Node ( kubelet ), ReplicaSet, DaemonSet.

Создал Dockerfile на основе python с web на порту 8000. ( omegathelegends/otus-web )
Создал манифест на основе созданого докерфайла с инит контейнером busybox и общей папкой emptyDir для редактирования index.html
По заданию со * , создан yaml с ENV которых не хватало длоя его запуска.

 -----------------------------------

### HW 10:

![image](https://user-images.githubusercontent.com/50916353/223554213-2c2e8b9e-5d28-45b4-b7d0-455ea5a67b97.png)
![image](https://user-images.githubusercontent.com/50916353/223554467-81907545-3ed3-4dbc-b9c1-149d085d30f5.png)
![image](https://user-images.githubusercontent.com/50916353/223554698-96c6f84f-3047-4d51-b3fc-03316a724f42.png)

Задание со звёздочкой:
Добавил обработку на изменение поля:
@kopf.on.field('otus.homework', 'v1', 'mysqls', field='spec.password')
при его выполнение собирается новый job добавленый в templates который меняет пароль. так же добавил отображение в статус.

для отображения статуса в CRD добавлены поля
          status:
              type: object
              x-kubernetes-preserve-unknown-fields: true
так же добавлены 
storageClassName в pvc и pv, что бы pvc не обрабатывался станартным SC 
