import os, sys
import time
import fitz
import json
import heapq
import html

ifname = sys.argv[1]  # get document filename
doc = fitz.open(ifname)  # open document
#out = open(fname + ".txt", "wb")  # open text output
#out = open(fname + ".txt", "w")  # open text output
print(sys.argv[1])
print(sys.argv[2])

texts = list()
x0_cnt = dict()
center_cnt = dict()
size_cnt = dict()

span_prev = None

for page in doc:  # iterate the document pages
    text = page.getText("dict")
    texts.append(text)
    for block in text.get("blocks"):
        #print(block.get("bbox"))
        if block.get("type") == 0:
            for line in block.get("lines"):
                for span in line.get("spans"):
                    bbox = span.get("bbox")
                    #print(str(bbox) + " " + span.get("text"))
                    #print(bbox[0])
                    x0_cnt[bbox[0]] = x0_cnt.get(bbox[0], 0) + 1
                    size_cnt[span.get("size", 0)] = size_cnt.get(span.get("size", 0), 0) + 1
                    center = bbox[0] + (bbox[2] - bbox[0]) / 2
                    span["center"] = center
                    center_cnt[center] = center_cnt.get(center, 0) + 1
                    #print(str(center) + " " + str(span))
                    if span_prev is not None:
                        y0_prev = span_prev.get("bbox")[1]
                        span_prev["lh"] = bbox[1] - y0_prev
                    span_prev = span

#for x0 in x0_cnt:
#    print(str(x0) + " " + str(x0_cnt[x0]))

x0_sorted = heapq.nlargest(2, x0_cnt, key=x0_cnt.__getitem__)
x0_sorted = sorted(x0_sorted)
#print(x0_sorted)
x0_para = x0_sorted[1]
x0_line = x0_sorted[0]

#for center in center_cnt:
#    print(str(center) + " " + str(center_cnt[center]))
center_sorted = heapq.nlargest(1, center_cnt, key=center_cnt.__getitem__)
center_line = center_sorted[0]

size_sorted = heapq.nlargest(1, size_cnt, key=size_cnt.__getitem__)
size_line = size_sorted[0]
#sys.exit()

ofname = sys.argv[2]
out = open(ofname, "w")
out.write("<html>\n<body>\n")

tag_stack = list()
def begin_tag(tagname, auto_end = True):
    if auto_end and len(tag_stack) > 0 and tag_stack[-1] == "p":
        end_tag()
    out.write("<" + tagname + ">")
    tag_stack.append(tagname)

def end_tag():
    if len(tag_stack) > 0:
        tagname = tag_stack.pop()
        out.write("</" + tagname + ">")

def print_text(text):
    if len(tag_stack) == 0:
        begin_tag("p")
    out.write(html.escape(text))

def is_in_p():
    if len(tag_stack) > 0 and tag_stack[-1] == "p":
        return True
    else:
        return False

y_cur = 0
footnote_mark = ""
footnote_text = ""
for text in texts:  # iterate the document pages
    for block in text.get("blocks"):
        if block.get("type") == 0:
            for line in block.get("lines"):
                for span in line.get("spans"):
                    if len(span.get("text", "").rstrip(' ')) == 0:
                        continue
                    bbox = span.get("bbox")
                    if span.get("font").find("Bold") > 0:
                        print()
                        if span.get("lh", 0) > (bbox[3] - bbox[1]) * 1.9:
                            begin_tag("h1")
                            print_text(span.get("text"))
                            end_tag()
                        else:
                            begin_tag("h2")
                            print_text(span.get("text"))
                            end_tag()
                        #print(span)
                    elif bbox[0] == x0_para and span.get("size", 0) == size_line:
                        #print()
                        #print("PARA " + span.get("text"), end = "")
                        
                        begin_tag("p")
                        print_text(span.get("text"))
                        
                        y_cur = span.get("bbox")[1]
                    elif bbox[0] == x0_line and span.get("size", 0) == size_line:
                        #print(span.get("text"), end = "")

                        print_text(span.get("text"))

                        y_cur = span.get("bbox")[1]
                    elif bbox[0] > x0_line and span.get("size", 0) < size_line:
                        #quote
                        # print()
                        # print("QUOTE " + span.get("text"), end = "")

                        if is_in_p():
                            begin_tag("sup", auto_end=False)
                            print_text("QUOTE " + span.get("text"))
                            end_tag()
                        elif len(footnote_mark) > 0:
                            footnote_text += span.get("text")
                        else:
                            begin_tag("p")
                            begin_tag("i", auto_end=False)
                            print_text("UNRECOG %.2f %.2f %.2f %.2f %s" % (x0_line, center_line, xn, xn_drift, str(span)))
                            end_tag()
                            end_tag()
                            
                    else:
                        bbox = span.get("bbox")
                        if bbox[1] == y_cur:    #text after quote etc.
                            # print(span.get("text"), end = "")
                            print_text(span.get("text"))
                        elif bbox[0] < x0_line and span.get("size", 0) < size_line:
                            if len(span.get("text")) > 1:
                                #continuation of footnote text
                                footnote_text += span.get("text")
                            else:
                                #beginning of footnote mark
                                if len(footnote_text) > 0:
                                    begin_tag("p")
                                    begin_tag("sub", auto_end=False)
                                    print_text("FOOTNOTE " + footnote_mark + footnote_text)
                                    end_tag()
                                    end_tag()
                                    footnote_mark = ""
                                    footnote_text = ""
                                footnote_mark = span.get("text")
                                footnote_text = ""
                        elif bbox[0] == x0_line and len(footnote_mark) > 0 and len(footnote_text) == 0:
                            #beginning of footnote text
                            footnote_text += span.get("text")
                        elif bbox[0] == x0_line and len(footnote_mark) > 0 and len(footnote_text) > 0:
                            #likely not footnote
                            if not is_in_p():
                                begin_tag('p')
                            begin_tag("sup", auto_end=False)
                            print_text("QUOTE " + span.get("text"))
                            end_tag()
                        else:
                            #center = bbox[0] + (bbox[2] - bbox[0]) / 2
                            center = span.get("center")
                            center_drift = abs(center / center_line - 1)
                            xn = bbox[2]
                            xn_drift = abs((xn - x0_line) / (center_line - x0_line) / 2 - 1)
                            if center_drift < 0.1:
                                #print()
                                #print("OTHER " + span.get("text"))
                                begin_tag("p")
                                begin_tag("i", auto_end=False)
                                print_text("OTHER %.2f %s" % (size_line, str(span)))
                                end_tag()
                                end_tag()
                            elif xn_drift < 0.1:
                                begin_tag("p")
                                begin_tag("i", auto_end=False)
                                print_text("ALIGNRIGHT " + span.get("text"))
                                end_tag()
                                end_tag()
                            else:
                                #print()
                                #print("---------------")
                                #print(span)
                                begin_tag("p")
                                begin_tag("i", auto_end=False)
                                print_text("UNRECOG %.2f %.2f %.2f %.2f %s" % (x0_line, center_line, xn, xn_drift, str(span)))
                                end_tag()
                                end_tag()
        else:
            begin_tag("p")
            begin_tag("i", auto_end=False)
            print_text("BLOCK %s" % (str(block)))
            end_tag()
            end_tag()

                        
    #out.write(json.dumps(text))
    #json.dump(text, out)
    #out.write(page.getTextPage().extractJSON())
    #out.write(bytes((12,)))  # write page delimiter (form feed 0x0C)
#out.close()
end_tag()
out.write("</body>\n</html>\n")
out.flush()
out.close()
