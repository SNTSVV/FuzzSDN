package edu.svv.fuzzsdn.common.utils;

import java.util.HashMap;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class SQL
{

    private static final HashMap<String, String> sqlTokens;
    private static final Pattern sqlTokenPattern;

    static
    {
        //MySQL escape sequences: http://dev.mysql.com/doc/refman/5.1/en/string-syntax.html
        String[][] search_regex_replacement = new String[][]
                {
                        //search string | search regex  | sql replacement regex
                        {   "\u0000"    , "\\x00"       , "\\\\0"               },
                        {   "'"         , "'"           , "\\\\'"               },
                        {   "\""        , "\""          , "\\\\\""              },
                        {   "\b"        , "\\x08"       , "\\\\b"               },
                        {   "\n"        , "\\n"         , "\\\\n"               },
                        {   "\r"        , "\\r"         , "\\\\r"               },
                        {   "\t"        , "\\t"         , "\\\\t"               },
                        {   "_"         , "_"           , "\\_"                 },
                        {   "\u001A"    , "\\x1A"       , "\\\\Z"               },
                        {   "\\"        , "\\\\"        , "\\\\\\\\"            }
                };

        sqlTokens = new HashMap<>();
        StringBuilder patternStr = new StringBuilder();
        for (String[] srr : search_regex_replacement)
        {
            sqlTokens.put(srr[0], srr[2]);
            patternStr.append((patternStr.length() == 0) ? "" : "|").append(srr[1]);
        }
        sqlTokenPattern = Pattern.compile('(' + patternStr.toString() + ')');
    }


    public static String filter(String s)
    {
        Matcher matcher = sqlTokenPattern.matcher(s);
        StringBuffer sb = new StringBuffer();
        while(matcher.find())
        {
            matcher.appendReplacement(sb, sqlTokens.get(matcher.group(1)));
        }
        matcher.appendTail(sb);
        return sb.toString();
    }

}
