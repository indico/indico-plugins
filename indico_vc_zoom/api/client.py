from __future__ import absolute_import, unicode_literals
from requests import Session
from requests.auth import HTTPBasicAuth

import contextlib
import json
import requests
import time
import jwt


class ApiClient(object):
    """Simple wrapper for REST API requests"""

    def __init__(self, base_uri=None, timeout=15, **kwargs):
        """Setup a new API Client

        :param base_uri: The base URI to the API
        :param timeout: The timeout to use for requests
        :param kwargs: Any other attributes. These will be added as
                           attributes to the ApiClient object.
        """
        self.base_uri = base_uri
        self.timeout = timeout
        for k, v in kwargs.items():
            setattr(self, k, v)

    @property
    def timeout(self):
        """The timeout"""
        return self._timeout

    @timeout.setter
    def timeout(self, value):
        """The default timeout"""
        if value is not None:
            try:
                value = int(value)
            except ValueError:
                raise ValueError("timeout value must be an integer")
        self._timeout = value

    @property
    def base_uri(self):
        """The base_uri"""
        return self._base_uri

    @base_uri.setter
    def base_uri(self, value):
        """The default base_uri"""
        if value and value.endswith("/"):
            value = value[:-1]
        self._base_uri = value

    def url_for(self, endpoint):
        """Get the URL for the given endpoint

        :param endpoint: The endpoint
        :return: The full URL for the endpoint
        """
        if not endpoint.startswith("/"):
            endpoint = "/{}".format(endpoint)
        if endpoint.endswith("/"):
            endpoint = endpoint[:-1]
        return self.base_uri + endpoint

    def get_request(self, endpoint, params=None, headers=None):
        """Helper function for GET requests

        :param endpoint: The endpoint
        :param params: The URL parameters
        :param headers: request headers
        :return: The :class:``requests.Response`` object for this request
        """
        if headers is None:
            headers = {"Content-Type": "application/json", "Authorization": "Bearer {}".format(self.config.get("token"))}
        return requests.get(
            self.url_for(endpoint), params=params, headers=headers, timeout=self.timeout
        )

    def post_request(
        self, endpoint, params=None, data=None, headers=None, cookies=None
    ):
        """Helper function for POST requests

        :param endpoint: The endpoint
        :param params: The URL parameters
        :param data: The data (either as a dict or dumped JSON string) to
                     include with the POST
        :param headers: request headers
        :param cookies: request cookies
        :return: The :class:``requests.Response`` object for this request
        """
        if data and not is_str_type(data):
            data = json.dumps(data)
        if headers is None:
            headers = {"Content-Type": "application/json", "Authorization": "Bearer {}".format(self.config.get("token"))}
        return requests.post(
            self.url_for(endpoint),
            params=params,
            data=data,
            headers=headers,
            cookies=cookies,
            timeout=self.timeout,
        )

    def patch_request(
        self, endpoint, params=None, data=None, headers=None, cookies=None
    ):
        """Helper function for PATCH requests

        :param endpoint: The endpoint
        :param params: The URL parameters
        :param data: The data (either as a dict or dumped JSON string) to
                     include with the PATCH
        :param headers: request headers
        :param cookies: request cookies
        :return: The :class:``requests.Response`` object for this request
        """
        if data and not is_str_type(data):
            data = json.dumps(data)
        if headers is None:
            headers = {"Content-Type": "application/json", "Authorization": "Bearer {}".format(self.config.get("token"))}
        return requests.patch(
            self.url_for(endpoint),
            params=params,
            data=data,
            headers=headers,
            cookies=cookies,
            timeout=self.timeout,
        )

    def delete_request(
        self, endpoint, params=None, data=None, headers=None, cookies=None
    ):
        """Helper function for DELETE requests

        :param endpoint: The endpoint
        :param params: The URL parameters
        :param data: The data (either as a dict or dumped JSON string) to
                     include with the DELETE
        :param headers: request headers
        :param cookies: request cookies
        :return: The :class:``requests.Response`` object for this request
        """
        if data and not is_str_type(data):
            data = json.dumps(data)
        if headers is None:
            headers = {"Content-Type": "application/json", "Authorization": "Bearer {}".format(self.config.get("token"))}
        return requests.delete(
            self.url_for(endpoint),
            params=params,
            data=data,
            headers=headers,
            cookies=cookies,
            timeout=self.timeout,
        )

    def put_request(self, endpoint, params=None, data=None, headers=None, cookies=None):
        """Helper function for PUT requests

        :param endpoint: The endpoint
        :param params: The URL paramaters
        :param data: The data (either as a dict or dumped JSON string) to
                     include with the PUT
        :param headers: request headers
        :param cookies: request cookies
        :return: The :class:``requests.Response`` object for this request
        """
        if data and not is_str_type(data):
            data = json.dumps(data)
        if headers is None:
            headers = {"Content-Type": "application/json", "Authorization": "Bearer {}".format(self.config.get("token"))}
        return requests.put(
            self.url_for(endpoint),
            params=params,
            data=data,
            headers=headers,
            cookies=cookies,
            timeout=self.timeout,
        )


@contextlib.contextmanager
def ignored(*exceptions):
    """Simple context manager to ignore expected Exceptions

    :param \*exceptions: The exceptions to safely ignore
    """
    try:
        yield
    except exceptions:
        pass


def is_str_type(val):
    """Check whether the input is of a string type.

    We use this method to ensure python 2-3 capatibility.

    :param val: The value to check wither it is a string
    :return: In python2 it will return ``True`` if :attr:`val` is either an
             instance of str or unicode. In python3 it will return ``True`` if
             it is an instance of str
    """
    with ignored(NameError):
        return isinstance(val, basestring)
    return isinstance(val, str)


def require_keys(d, keys, allow_none=True):
    """Require that the object have the given keys

    :param d: The dict the check
    :param keys: The keys to check :attr:`obj` for. This can either be a single
                 string, or an iterable of strings

    :param allow_none: Whether ``None`` values are allowed
    :raises:
        :ValueError: If any of the keys are missing from the obj
    """
    if is_str_type(keys):
        keys = [keys]
    for k in keys:
        if k not in d:
            raise ValueError("'{}' must be set".format(k))
        if not allow_none and d[k] is None:
            raise ValueError("'{}' cannot be None".format(k))
    return True


def date_to_str_gmt(d):
    """Convert date and datetime objects to a string

    Note, this does not do any timezone conversion.

    :param d: The :class:`datetime.date` or :class:`datetime.datetime` to
              convert to a string
    :returns: The string representation of the date
    """
    return d.strftime("%Y-%m-%dT%H:%M:%SZ")

def date_to_str_local(d):
    """Convert date and datetime objects to a string

    Note, this does not do any timezone conversion.

    :param d: The :class:`datetime.date` or :class:`datetime.datetime` to
              convert to a string
    :returns: The string representation of the date
    """
    return d.strftime("%Y-%m-%dT%H:%M:%S")


def generate_jwt(key, secret):
    header = {"alg": "HS256", "typ": "JWT"}

    payload = {"iss": key, "exp": int(time.time() + 3600)}

    token = jwt.encode(payload, secret, algorithm="HS256", headers=header)
    return token.decode("utf-8")





class APIException(Exception):
    pass


class RoomNotFoundAPIException(APIException):
    pass





class BaseComponent(ApiClient):
    """A base component"""

    def __init__(self, base_uri=None, config=None, timeout=15, **kwargs):
        """Setup a base component

        :param base_uri: The base URI to the API
        :param config: The config details
        :param timeout: The timeout to use for requests
        :param kwargs: Any other attributes. These will be added as
                           attributes to the ApiClient object.
        """
        super(BaseComponent, self).__init__(
            base_uri=base_uri, timeout=timeout, config=config, **kwargs
        )

    def post_request(
        self, endpoint, params=None, data=None, headers=None, cookies=None
    ):
        """Helper function for POST requests

        Since the Zoom.us API only uses POST requests and each post request
        must include all of the config data, this method ensures that all
        of that data is there

        :param endpoint: The endpoint
        :param params: The URL parameters
        :param data: The data (either as a dict or dumped JSON string) to
                     include with the POST
        :param headers: request headers
        :param cookies: request cookies
        :return: The :class:``requests.Response`` object for this request
        """
        params = params or {}
        if headers is None:
            headers = {"Content-Type": "application/json", "Authorization": "Bearer {}".format(self.config.get("token"))}
        return super(BaseComponent, self).post_request(
            endpoint, params=params, data=data, headers=headers, cookies=cookies
        )

class MeetingComponent(BaseComponent):
    def list(self, **kwargs):
        require_keys(kwargs, "user_id")
        return self.get_request(
            "/users/{}/meetings".format(kwargs.get("user_id")), params=kwargs
        )

    def create(self, **kwargs):
        require_keys(kwargs, "user_id")
        if kwargs.get("start_time"):
            if kwargs.get("timezone"):
                kwargs["start_time"] = date_to_str_local(kwargs["start_time"])
            else:
                kwargs["start_time"] = date_to_str_gmt(kwargs["start_time"])
        return self.post_request(
            "/users/{}/meetings".format(kwargs.get("user_id")), params=kwargs['user_id'], data={x: kwargs[x] for x in kwargs.keys() if x not in ['user_id']}
        )

    def get(self, **kwargs):
        require_keys(kwargs, "id")
        return self.get_request("/meetings/{}".format(kwargs.get("id")), params=kwargs)

    def update(self, **kwargs):
        require_keys(kwargs, "id")
        if kwargs.get("start_time"):
            if kwargs.get("timezone"):
                kwargs["start_time"] = date_to_str_local(kwargs["start_time"])
            else:
                kwargs["start_time"] = date_to_str_gmt(kwargs["start_time"])
        return self.patch_request(
            "/meetings/{}".format(kwargs.get("id")), params=kwargs
        )

    def delete(self, **kwargs):
        require_keys(kwargs, "id")
        return self.delete_request(
            "/meetings/{}".format(kwargs.get("id")), params=kwargs
        )

    def get_invitation(self, **kwargs):
        require_keys(kwargs, "id")
        return self.get_request("/meetings/{}/invitation".format(kwargs.get("id")), params=kwargs)


class UserComponent(BaseComponent):
    def list(self, **kwargs):
        return self.get_request("/users", params=kwargs)

    def create(self, **kwargs):
        return self.post_request("/users", params=kwargs)

    def update(self, **kwargs):
        require_keys(kwargs, "id")
        return self.patch_request("/users/{}".format(kwargs.get("id")), params=kwargs)

    def delete(self, **kwargs):
        require_keys(kwargs, "id")
        return self.delete_request("/users/{}".format(kwargs.get("id")), params=kwargs)

    def get(self, **kwargs):
        require_keys(kwargs, "id")
        return self.get_request("/users/{}".format(kwargs.get("id")), params=kwargs)



class ZoomClient(ApiClient):
    """Zoom.us REST API Python Client"""

    """Base URL for Zoom API"""

    def __init__(
        self, api_key, api_secret, data_type="json", timeout=15
    ):
        """Create a new Zoom client

        :param api_key: The Zooom.us API key
        :param api_secret: The Zoom.us API secret
        :param data_type: The expected return data type. Either 'json' or 'xml'
        :param timeout: The time out to use for API requests
        """
        
        BASE_URI = "https://api.zoom.us/v2"
        self.components = {"user": UserComponent,
                           "meeting": MeetingComponent}

        super(ZoomClient, self).__init__(base_uri=BASE_URI, timeout=timeout)

        # Setup the config details
        self.config = {
            "api_key": api_key,
            "api_secret": api_secret,
            "data_type": data_type,
            "token": generate_jwt(api_key, api_secret),
        }

        # Instantiate the components
        for key in self.components.keys():
            self.components[key] = self.components[key](
                base_uri=BASE_URI, config=self.config
            )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return

    def refresh_token(self):
        self.config["token"] = (
            generate_jwt(self.config["api_key"], self.config["api_secret"]),
        )

    @property
    def api_key(self):
        """The Zoom.us api_key"""
        return self.config.get("api_key")

    @api_key.setter
    def api_key(self, value):
        """Set the api_key"""
        self.config["api_key"] = value
        self.refresh_token()

    @property
    def api_secret(self):
        """The Zoom.us api_secret"""
        return self.config.get("api_secret")

    @api_secret.setter
    def api_secret(self, value):
        """Set the api_secret"""
        self.config["api_secret"] = value
        self.refresh_token()

    @property
    def meeting(self):
        """Get the meeting component"""
        return self.components.get("meeting")

    @property
    def user(self):
        """Get the user component"""
        return self.components.get("user")



class ZoomIndicoClient(object):
    def __init__(self, settings):
        api_key=settings.get('api_key')
        api_secret=settings.get('api_secret')    
        self.client=ZoomClient(api_key, api_secret)

    def create_meeting(self, **kwargs):
        return json.loads(self.client.meeting.create(**kwargs).content)

    
    def get_meeting(self, zoom_id):
        return json.loads(self.client.meeting.get(id=zoom_id).content)

    
    def get_meeting_invitation(self, zoom_id):
        return json.loads(self.client.meeting.get_invitation(id=zoom_id).content)

    def delete_meeting(self, zoom_id):
        self.client.meeting.delete(id=zoom_id)

    def check_user_meeting_time(self, userID, start_dt, end_dt):
        pass


