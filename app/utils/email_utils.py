from templated_email import send_templated_mail


def send_email(
    send_from: str, send_to: str, template_name: str = "welcome", data: dict = {}
):
    try:
        send_templated_mail(
            template_name=template_name,
            from_email=send_from,
            recipient_list=[send_to],
            context=data,
        )
        return True, None
    except Exception as e:
        return False, str(e)
