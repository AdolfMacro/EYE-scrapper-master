CITY_COORDS = {

    "تبریز": {
        "lat": 38.0800,
        "lon": 46.2919
    },

    "ارومیه": {
        "lat": 37.5527,
        "lon": 45.0760
    },

    "تهران": {
        "lat": 35.6892,
        "lon": 51.3890
    }

}


def get_location(city):

    return CITY_COORDS.get(
        city,
        None
    )