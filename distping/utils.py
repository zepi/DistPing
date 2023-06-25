def getPath(category, target):
    if 'key' in category:
        categoryKey = category['key']
    else:
        categoryKey = category['name']

    if 'key' in target:
        targetKey = target['key']
    else:
        targetKey = target['name']

    return categoryKey + '/' + targetKey

def roundTime(time):
    if isinstance(time, str):
        time = float(time)

    if time > 99:
        time = round(time, 0)
    if time > 9:
        time = round(time, 1)
    else:
        time = round(time, 2)

    return '%g'%(time)
