import kopf
import yaml
import kubernetes
import time
from jinja2 import Environment, FileSystemLoader


def wait_until_job_end(jobname):
    api = kubernetes.client.BatchV1Api()
    job_finished = False
    jobs = api.list_namespaced_job('default')
    while (not job_finished) and \
            any(job.metadata.name == jobname for job in jobs.items):
        time.sleep(1)
        jobs = api.list_namespaced_job('default')
        for job in jobs.items:
            if job.metadata.name == jobname:
                print(f"job with { jobname }  found,wait untill end")
                if job.status.succeeded == 1:
                    print(f"job with { jobname }  success")
                    job_finished = True


def render_template(filename, vars_dict):
    env = Environment(loader=FileSystemLoader('./templates'))
    template = env.get_template(filename)
    yaml_manifest = template.render(vars_dict)
    json_manifest = yaml.safe_load(yaml_manifest)
    return json_manifest


def delete_success_jobs(mysql_instance_name):
    print("start deletion")
    api = kubernetes.client.BatchV1Api()
    jobs = api.list_namespaced_job('default')
    for job in jobs.items:
        jobname = job.metadata.name
        if (jobname == f"backup-{mysql_instance_name}-job") or \
                (jobname == f"restore-{mysql_instance_name}-job"):
            if job.status.succeeded == 1:
                api.delete_namespaced_job(jobname,
                                          'default',
                                          propagation_policy='Background')
                
@kopf.on.field('otus.homework', 'v1', 'mysqls', field='spec.password')
def change_pass(body, old, new, **_):
    name = body['metadata']['name']
    image = body['spec']['image']
    database = body['spec']['database']
    old_pass = old
    new_pass = new

    if old_pass and new_pass:
        change_pass_job = render_template('mysql-pass-changer.yml.j2',
                                          { 'name': name,
                                            'image': image,
                                            'database': database,
                                            'old_pass': old_pass,
                                            'new_pass': new_pass })
        
        change_pass_job_name = change_pass_job['metadata']['name']
        api = kubernetes.client.BatchV1Api()
        try:
            api.delete_namespaced_job(change_pass_job_name, 'default', propagation_policy='Background')
        except kubernetes.client.rest.ApiException:
            pass

        try:
            api.create_namespaced_job('default', change_pass_job)
            wait_until_job_end(change_pass_job_name)
        except kubernetes.client.rest.ApiException:
            pass
        return {'message': 'Password has been changed.'}
        


@kopf.on.create('otus.homework', 'v1', 'mysqls')
# Функция, которая будет запускаться при создании объектов тип MySQL:
def mysql_on_create(body, spec, **kwargs):
    name = body['metadata']['name']
    image = body['spec']['image']
    password = body['spec']['password']
    database = body['spec']['database']
    storage_size = body['spec']['storage_size']

    # Генерируем JSON манифесты для деплоя
    persistent_volume = render_template('mysql-pv.yml.j2',
                                        {'name': name,
                                         'storage_size': storage_size})
    persistent_volume_claim = render_template('mysql-pvc.yml.j2',
                                              {'name': name,
                                               'storage_size': storage_size})
    service = render_template('mysql-service.yml.j2', {'name': name})

    deployment = render_template('mysql-deployment.yml.j2', {
        'name': name,
        'image': image,
        'password': password,
        'database': database})
    restore_job = render_template('restore-job.yml.j2', {
        'name': name,
        'image': image,
        'password': password,
        'database': database})

    # Определяем, что созданные ресурсы являются дочерними к управляемому CustomResource:
    kopf.append_owner_reference(persistent_volume, owner=body)
    kopf.append_owner_reference(persistent_volume_claim, owner=body)  # addopt
    kopf.append_owner_reference(service, owner=body)
    kopf.append_owner_reference(deployment, owner=body)
    kopf.append_owner_reference(restore_job, owner=body)
    # ^ Таким образом при удалении CR удалятся все, связанные с ним pv,pvc,svc, deployments

    api = kubernetes.client.CoreV1Api()
    # Создаем mysql PV:
    api.create_persistent_volume(persistent_volume)
    # Создаем mysql PVC:
    api.create_namespaced_persistent_volume_claim('default', persistent_volume_claim)
    # Создаем mysql SVC:
    api.create_namespaced_service('default', service)

    # Создаем mysql Deployment:
    api = kubernetes.client.AppsV1Api()
    api.create_namespaced_deployment('default', deployment)

    # Cоздаем PVC  и PV для бэкапов:
    try_restore = True
    try:
        backup_pv = render_template('backup-pv.yml.j2', {'name': name})
        api = kubernetes.client.CoreV1Api()
        api.create_persistent_volume(backup_pv)
        try_restore = False
    except kubernetes.client.rest.ApiException:
        pass

    try:
        backup_pvc = render_template('backup-pvc.yml.j2', {'name': name, 'storage_size': storage_size})
        api = kubernetes.client.CoreV1Api()
        api.create_namespaced_persistent_volume_claim('default', backup_pvc)
    except kubernetes.client.rest.ApiException:
        pass

    # Пытаемся восстановиться из backup
    backup_status = 'No info'
    if try_restore:
        restore_job_name = restore_job['metadata']['name']
        try:
            api = kubernetes.client.BatchV1Api()
            api.create_namespaced_job('default', restore_job)
            wait_until_job_end(restore_job_name)
            backup_status = 'Backup успешно восстановлен.'
        except kubernetes.client.rest.ApiException:
            backup_status = 'Ошибка восстановления Backup.'
            pass
    else:
        backup_status = 'MySQL установлена без backup'


    return {'message': backup_status}

@kopf.on.delete('otus.homework', 'v1', 'mysqls')
def delete_object_make_backup(body, **kwargs):
    name = body['metadata']['name']
    image = body['spec']['image']
    password = body['spec']['password']
    database = body['spec']['database']

    delete_success_jobs(name)

    # Cоздаем backup job:
    api = kubernetes.client.BatchV1Api()
    backup_job = render_template('backup-job.yml.j2', {
        'name': name,
        'image': image,
        'password': password,
        'database': database})
    api.create_namespaced_job('default', backup_job)
    wait_until_job_end(f"backup-{name}-job")

    # delete pv ( if no auto delete with remove pvc)
    try:
        api = kubernetes.client.CoreV1Api()
        api.delete_persistent_volume(f'{name}-pv')
    except kubernetes.client.rest.ApiException:
        pass
    return {'message': "mysql and its children resources deleted"}