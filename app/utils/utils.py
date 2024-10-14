import re


def wrap_image_in_div(html_string):
    try:
        # Define the regex pattern for finding image elements
        img_pattern = r"<img[^>]*>"

        # Find all image elements in the HTML string
        img_matches = re.findall(img_pattern, html_string)

        # Iterate through the matches and replace each image element
        for img_match in img_matches:
            old_img_tag = img_match

            # Wrap the image in a div and add styles
            new_img_tag = f'<div style="display: flex; position: relative; height: 1.5vw;"><p>{img_match}</p></div>'

            # Add width and height styles to the img tag
            new_img_tag = new_img_tag.replace("<img ", '<img style="width: 100%; height: 100%; " ')

            # Replace the old img tag with the new one in the HTML string
            html_string = html_string.replace(old_img_tag, new_img_tag)

    except Exception:
        # If any error occurs, return the original HTML string
        return html_string

    return html_string
