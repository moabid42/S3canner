

rule dummyrule
{
    strings:
        $my_text_string = "I am malicious"

    condition:
        $my_text_string
}