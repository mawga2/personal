import win32com.client

def send_notification(subject, body):
    ol=win32com.client.Dispatch("outlook.application")
    olmailitem=0x0 #size of the new email
    newmail=ol.CreateItem(olmailitem)
    newmail.Subject= subject
    newmail.To='u3606179@connect.hku.hk'
    newmail.Body= body

    newmail.Send()