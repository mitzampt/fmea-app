#!/usr/bin/python3
# Maintenance and Reliability Tools
# SPDX-License-Identifier: MIT
# Coyright 2023 Mihai-Gabriel Vasile [mihaigabriel.vasile23&at;gmail.com]
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the
# Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Preamble: Perform tests to see if the script is called in an initialized env

if __name__ == '__main__':
    print('MRTools, version:0.2.0')

# Utility classes
class AttrAccess:
    def __init__(self):
        self.__doc__ = 'Attribute Access: Allow enumeration of attributes for any class'
        for field in self.__nodeattrs__():
            self[field] = None
    def __copy__(self):
        new = self.__class__()
        for f in self.__nodeattrs__():
            new[f]=self[f]
        return new
    def __nodename__(self):
        return self.__class__.__name__.lower()
    def __nodeattrs__(self,extra_filter = None):
        # enumerate class fields, exclude private and special fields as well as functions
        if extra_filter is None:
            return list(filter(lambda y:(y[0]!='_' and not callable(self[y])),dir(self)))
        if not callable(extra_filter):
            return list(filter(lambda y:(y[0]!='_' and not callable(self[y])),dir(self)))
        return list(filter(lambda y: (y[0]!='_' and not callable(self[y]) and \
                                      extra_filter(self[y])),dir(self)))
    def __contains__(self,key):
        return key in self.__nodeattrs__()
    def __getitem__(self,item):
        # allow usage of subscript
        return self.__getattribute__(item)
    def __setitem__(self,item,value):
        # subscript allows to change
        return self.__setattr__(item,value)
    def __nodetolist__(self):
        # return all atribute values as a list
        return list(self[fieldname] for fieldname in self.__nodeattrs__())
    def __nodetodict__(self):
        return dict(zip(self.__nodeattrs__(),self.__nodetolist__()))
    def __nodeinband__(self,inlist,overwrite=False,debug=False):
        # allow initialization of all structures by list, tuple or dict
        if inlist is None:
            return self
        fields = self.__nodeattrs__()
        inlist_type = type(inlist).__name__.lower()
        if inlist_type.find('list')>=0 or inlist_type.find('tuple')>=0\
            and len(fields)>=len(inlist):
            # TODO: Some more checks here
            i = 0;
            for fieldname in fields:
                try:
                    if type(self[fieldname]) != type(None):
                        self[fieldname] = self[fieldname].__class__(inlist[i])
                    else:
                        self[fieldname] = inlist[i]
                except Exception as e:
                    if overwrite:
                        self[fieldname] = None
                    else:
                        self[fieldname] = inlist[i]
                    print(f'WARNING: Node-in-band could not convert saying {e.args} as {e.__class__.__name__}')
                finally:
                    i+=1
                    continue
        if inlist_type.find('dict') >=0 and len(fields)>=len(inlist):
            for fieldname in fields:
                inf = inlist.get(fieldname,None)
                if inf is None:
                    if overwrite:
                        self[fieldname] = None
                    else:
                        if debug: print(f'WARNING: Mismatch in dict and self on fieldname {fieldname}')
                else:
                    try:
                        if type(self[fieldname]) == type(None):
                            self[fieldname] = inf
                        else:
                            self[fieldname] = self[fieldname].__class__(inf)
                    except Exception as e:
                        if overwrite:
                            self[fieldname] = None
                        else:
                            self[fieldname] = inf
                        print(f'WARNING: Node-in-band could not convert saying {e.args} as {e.__class__.__name__}')
                    finally:
                        continue
        return self
    def __nodetypes__(self):
        # return python data types
        return list(type(self[field]).__name__ for field in self.__nodeattrs__())
    def __str__(self):
        # return a string representation of the object
        name     = self.__class__.__name__
        contents = self.__strvalues__()
        return f'{name}({contents})'
    def __strfields__(self):
        return ', '.join(self.__nodeattrs__())
    def __strvalues__(self):
        return ', '.join(f'{key[0]}=\'{key[1]}\'' for key in self.__nodetodict__().items())
    def __htmlid__(self,elem='div'):
        idstr = ''.join(filter(lambda c:c.isupper() or c.isdigit(), self.__class__.__name__))\
                  .lower()
        if self.__contains__('id'):
            return f'{elem}-{idstr}-{self["id"]}'
        else:
            return f'id={elem}-{idstr}-{self.__hash__()}'
    def __htmlspan__(self,css_class='',field_filter=None,use_raw=True):
        if css_class != '':
            css_class = f' class=\"{css_class}\"'
        fields = self.__nodetodict__()
        if field_filter is not None and callable(field_filter):
            fields = dict(filter(field_filter,fields))
        fieldstr='</p><p>'.join(fv for fv in fields.values())
        fieldstr=f'<p>{fieldstr}</p>'
        if use_raw:
            rawstr = f' rawdata={str(self)}'
        else:
            rawstr = ''
        return f'<span id="{self.__htmlid__("span")}"{css_class}{rawstr}>{fieldstr}</span>'
    def __htmltr__(self,field_filter=None,apply_to_cell=None):
        print(f'DEBUG: Called row with {field_filter} and {apply_to_cell}')
        fields = self.__nodetodict__()
        if field_filter is not None and callable(field_filter):
            fields = dict(filter(field_filter,fields.items()))
        if apply_to_cell is not None and callable(apply_to_cell):
            cell_content = "</td><td>".join(apply_to_cell(self,fv) for fv in fields.values())
        else:
            cell_content = "</td><td>".join(str(fv) for fv in fields.values())
        return f'<tr><td>{cell_content}</td></tr>'

class Sqlite3Access(AttrAccess):
    id = None
    _dbname_ = ''
    _sqlite3_ = None
    _cursor_ = None
    _prevquery_ = ''
    def __init__(self):
        self.__doc__ = 'Sqlite3 Access: Allow enumeration and operations for sqlite3'
    def __sqlitefields__(self):
        # use attribute access to enumerate fields
        return self.__strfields__()
    def __sqlitetypes__(self):
        # detect field types and constraints
        result = ''
        for fieldname in self.__nodeattrs__():
            if fieldname == 'id':
                fieldtype ='INT PRIMAY KEY NOT NULL'
            else:
                if fieldname.lower().find('id') > 0 or \
                   fieldname.lower().find('count') > 0 or \
                   fieldname.lower().find('_num') > 0 or \
                   fieldname.lower().find('_amt') > 0 or \
                   fieldname.lower().find('_score') > 0 or \
                   type(self[fieldname]).__name__.title().find('Int') >= 0 :
        # TODO: Find better detection/mapping to use here
                    fieldtype = 'INT'
                else:
                    fieldtype = 'VARCHAR'
            if result == '':
                result = f'{fieldname} {fieldtype}'
            else:
                result = f'{result},{fieldname} {fieldtype}'
        return result
    def __sqlitetable__(self):
        # return the table name of current class
        return self.__nodename__().lower()
    def __sqlitequery__(self,operation='SELECT',what_clause='*', \
            from_clause ='', where_clause='', order_by='', values='',debug=False):
        # construct a query string
        if what_clause == '':
            what_clause = self.__sqlitefields__()
        if from_clause == '' and 'SELECT, DELETE'.find(operation) >= 0:
            from_clause = self.__sqlitetable__()
        result = f'{operation} {what_clause}'
        if from_clause != '':
            result = f'{result} FROM {from_clause}'
        if where_clause != '':
            result = f'{result} WHERE {where_clause}'
        if values != '':
            result = f'{result} VALUES({values})'
        if order_by != '':
            result = f'{result} ORDER BY {order_by}'
        if debug:
            print(f'DEBUG: Generated query"{result}"')
        return result
    def __sqlitevalidcur__(self,cursor=None,query=''):
        # see if current cursor is valid for fetching data
        if cursor is None:
            if self._cursor_ is None:
                return False
            else:
                cursor = self._cursor_
        if cursor != self._cursor_:
            self._cursor_ = cursor
        return True # TODO: Prevent thrashing the query loop
        if query != '' and query != self._prevquery_:
            self._prevquery_ = self.__sqlitequery__()
            try:
                cursor = cursor.execute(self._prevquery_)
            except Exception as e:
                print(f'''ERROR: Valid Cursor threw {e.__class__.__name__} saying
                {e.args}
                ''')
                return False
            else:
                if query.find(', '.join(f[0] for f in cursor.description)) < 0:
                    return False
        # TODO: Have more ways to validate the cursor and its query
        return True
    def __sqlitekeys__(self,cursor,debug=False):
        # create a dict to use positional search
        result = dict()
        test_cond = self._prevquery_.find(f'FROM {self.__sqlitetable__()}')
        if debug:
            print(f'''DEBUG: Searching "FROM {self.__sqlitetable__()}" in "{self._prevquery_}"
            returns {test_cond}
        ''')
        if test_cond<0:
            self._prevquery_ = self.__sqlitequery__()
            try:
                cursor = cursor.execute(self._prevquery_)
            except Exception as e:
                print(f'''ERROR: Cursor Keys threw {e.__class__.__name__} saying
                    {e.args}
                ''')
            else:
                for f in cursor.description:
                    result[f[0]]=result.__len__()
            finally:
                return result
        else:
            for f in cursor.description:
                result[f[0]]=result.__len__()
            return result
    def __sqlitenextid__(self,cursor,extra_where='',silent=False):
        # get the next available id to create a new object
        self._prevquery_ = self.__sqlitequery__(what_clause='max(id)')
        if cursor is not None:
            # we don't care if the query has already executed
            try:
                record = cursor.execute(self._prevquery_).fetchone()
                if record[0] is None and silent:
                    return None
                else:
                    return record[0]+1
            except Exception as e:
                print(f'''ERROR: Next ID threw {e.__class__.__name__} saying
                {e.args}
                ''')
        return None # This ensures an error
    def __sqlitenext__(self,cursor,extra_where='',debug=False):
        # mutate self and set current id by select firstrow()
        query = self.__sqlitequery__(what_clause='',where_clause=extra_where,order_by='id ASC')
        if self.__sqlitevalidcur__(cursor,query):
            if self._prevquery_.find(query) <0:
                self._prevquery_=query
                try:
                    if debug: print(f'DEBUG: Executing {query}')
                    cursor = cursor.execute(query)
                except Exception as e:
                    print(f'''ERROR: Next record threw {e.__class__.__name__} saying
                    {e.args}
                    ''')
                    return None # invalid result
            keys = self.__sqlitekeys__(cursor) # should reuse cursor
            at_least_one = False
            for first_row in cursor.fetchmany():
                if len(first_row) == 0:
                    return None
                #use fetchmany because default=1row
                for fieldname in self.__sqlitefields__().split(', '):
                    column = keys.get(fieldname,None)
                    if column is None:
                        print(f'ERROR: query({query}) did not contain key {fieldname}')
                    #print(f'DEBUG: Fieldname {fieldname} ')
                    self[fieldname] = first_row[column]
                at_least_one = True
            if at_least_one:
                return cursor
        return None # invalid cursor or no more results
    def __sqliteself__(self,cursor,extra_where=''):
        # mutate self and return select result on self.id and extra_where
        where_cl = f'id = {self.id}'
        if extra_where != '':
            where_cl = f'{where_cl} AND {extra_where}'
        return self.__sqlitenext__(cursor,where_cl)
    def __sqliteupdate__(self,cursor,extra_where=''):
        # update database from self
        if self.id == None:
            self.id = self.__sqlitenextid__(cursor,extra_where)
        qw = f'{self.__sqlitetable__()}({self.__sqlitefields__()})'
        qv = ', '.join('?'*len(self.__nodeattrs__()))
        # qe = f' id = {self.id}' # not necessary for replace
        query = self.__sqlitequery__(operation = 'REPLACE INTO',\
                                     what_clause = qw, values = qv)
        if cursor is not None:
            self._prevquery_ = query
            try:
                cursor = cursor.execute(query,self.__nodetolist__())
                cursor.connection.commit()
            except Exception as e:
                print(f'''ERROR: Node Update failed on query {query} saying
                Exception type {e.__class__.__name__} - {e.args}
                ''')
            finally:
                return cursor
        return None #cursor was already None
    def __sqlitedelself__(self,cursor,extra_where=''):
        # remove from database self record
        if self.id is not None:
            query = f'DELETE FROM {self.__sqlitetable__()} WHERE id = {self.id}'
            if extra_where != '':
                query = f'{query}, {extra_where}'
            if cursor is not None:
                self._prevquery_ = query
                try:
                    cursor = cursor.execute(query)
                    cursor.connection.commit()
                except Exception as e:
                    print(f'''ERROR: Node delete failed on query {query} saying
                    Exception type  {e.__class__.__name__} - {e.args}''')
                finally:
                    return cursor
        print('ERROR: attempted delete on id = None or no cursor')
        return cursor
    def __sqlitecreate__(self,cursor):
        # return the create table query
        query_types = self.__sqlitetypes__()
        query_table = self.__sqlitetable__()
        query = f'CREATE TABLE {query_table}({query_types})'
        if cursor is None:
            print('WARNING: Cannot check if table exists')
        else:
            # stage 1: check if table already exists
            self._prevquery_ = query
            try:
                cursor = cursor.execute('SELECT * FROM sqlite_master')
            except Exception as e:
                print(f'''ERROR: Table create failed on query {query} saying
                Exception type {e.__class__.__name__} - {e.args}''')
            else:
                found = False
                for master_record in cursor.fetchall():
                    if master_record[0].lower() == 'table' and \
                        master_record[2] == query_table:
                        if master_record[4].find(query) < 0:
                            print("WARNING: Found ({master_record})")
                            found = True
                        else:
                            query = 'SELECT \"TABLE EXISTS\"'
                if found:
                    # TODO: find a way to alter the table
                    create_query = None
                    for c in master_record[4]:
                        if c == '(':
                            create_query = ''
                        if create_query is not None:
                            if c == ')':
                                break
                            else:
                                create_query += c
                    if create_query is not None:
                        to_delete = []
                        to_add = []
                        to_rename = []
                        for cf in create_query.split(','):
                            if query_types.find(cf) < 0:
                                to_delete.append(cf)
                        for qt in query_types.split(','):
                            if create_query.find(qt) < 0:
                                to_add.append(qt)
                        for i in range(min(len(to_delete),len(to_add))):
                            # TODO: filter by types
                            td = to_delete.pop()
                            ta = to_add.pop()
                            to_rename.append((td,ta))
                        print(f'''WARNING: To add \"{to_add}\",
                                    to delete \"{to_delete}\",
                                    to rename \"{to_rename}\"''')
                        query = 'SELECT \"INVALID QUERY\"'
        return query

class OneToMany(Sqlite3Access):
    parentid = None
    parentclass = None
    _many_ = []
    def __init__(self):
        self.__doc__ = 'OneToMany: Manage self like a list '
    def __otmattach__(self,many,with_parentclass=False):
        # attach self to a list of objects, saves the list internally
        many.append(self)
        self._many_=many
        # parentclass update assumes ids between FMEA_Function and FMEA_Failure_Mode
        # do not overlap
        presumed_parents = list(filter(lambda x:x.id==self.parentid,many))
        if len(presumed_parents)>0 and with_parentclass:
            self._parentclass_ = presumed_parents[0].__class__.__name__
        return many
    def __otmpeers__(self,many=None,parentid=None,\
                                           parentclass=None):
        # list all nodes sharing parentid and parentclass
        if many is None:
            many = self._many_
        if parentid is None:
            parentid = self.parentid
        if parentclass is None:
            parentclass = self.parentclass
        return list(filter(lambda x:(x.parentid==parentid and\
                                     x.parentclass==parentclass),many))
    def __htmltable__(self,many=None,css_style='',field_filter=None,apply_to_cell=None):
        # render a table of the data
        if many is None:
            many = self._many_
        attributes = self.__nodetodict__()
        if field_filter is not None and callable(field_filter):
            attributes = dict(filter(field_filter,attributes.items()))
        headers = '</th><th>'.join(list(a.replace('_',' ').title() for a in attributes.keys()))
        if headers == '':
            headers = 'Nothing available'
        headers = f'<tr><th>{headers}</th></tr>'
        data = ''.join(list(r.__htmltr__(field_filter=field_filter,\
                                         apply_to_cell=apply_to_cell) for r in many))
        return f'''<table {self.__htmlid__("table")}{css_style}>
         <thead>{headers}</thead>
         <tbody>{data}</tbody>
        </table>'''

class ManyToMany(Sqlite3Access):
    parentlist = ''
    parentclass = ''
    _many_ = []
    def __init__(self):
        self.__doc__ = 'ManyToMany: Manage self like a list with several parent references'
    def __mtmattach__(self,many):
        # attach self to a list of objects, saves the list internally
        many.append(self)
        self._many_=many
        return many
    def __mtmparents__(self,many=None,parentclass=None):
        # list all parents of self
        if many is None:
            many = self._many_
        if parentclass is None:
            parentclass = self.parentclass
        return list(filter(lambda x:(str(x.id) in self.parentlist.split(', ')\
         and x.__class__.__name__ == parentclass if parentclass is not None\
         else True),many))
    def __mtmanypeers__(self,parentlist=None,parentclass=None):
        # list all peers of self by parentid
        if parentlist is None:
            parentlist = self.parentlist
        if parentclass is None:
            parentclass = self.parentclass
        return list(filter(lambda x:((y in parentlist.split(', ')\
         for y in x.parentlist.split(', ')) and x.__class__.__name__ ==\
         parentclass if parentclass is not None else True),many))
    def __mtmaddparent__(self,id):
        # TODO: This doesn't work properly
        if id is None:
            return self.parentlist
        if self.parentlist is None or self.parentlist == '':
            self.parentlist=str(id)
        else:
            self.parentlist = f'{self.parentlist}, {str(id)}'
        return self.parentlist
    def __mtmdelparent__(self,id):
        # TODO: This doesn't work properly
        if self.parentlist == id: return '' # cheaty optimization
        self.parentlist=', '.join(list(filter(lambda x:x.strip().startswith(str(id))\
         and x.strip().endswith(str(id)),self.parentlist.split(','))))
        return self.parentlist
    def __htmltable__(self,many=None,css_style='',field_filter=None,apply_to_cell=None):
        # render a table of the data
        if many is None:
            many = self._many_
        attributes = self.__nodetodict__()
        if field_filter is not None and callable(field_filter):
            attributes = dict(filter(field_filter,attributes))
        headers = '</th><th>'.join(attributes.keys().replace('_',' ').title())
        if headers == '':
            headers = 'Nothing available'
        headers = f'<tr><th>{headers}</th></tr>'
        try:
            newmany = sorted(many,key=lambda x:x.__mtmparents__())
        except Exception as e:
            print(f'''ERROR: Sorting for table failed with {e.__class__.__name__} saying:
            {e.args}''')
        else:
            many = newmany
        data = ''.join(list(r.__htmltr__(field_filter=field_filter,\
                                         apply_to_cell=apply_to_cell) for r in many))
        return f'''<table {self.__htmlid__("table")}{css_style}>
         <thead>{headers}</thead>
         <tbody>{data}</tbody>
        </table>'''

class TreeLeaf(OneToMany):
    _path_ = []
    def __init__(self):
        self.__doc__='TreeLeaf: Manage self as a leaf in a tree'
    def __leafpath__(self):
        if not self.__leafisvalid__():
            self.__treetraverse__(self._many_)
        return self._path_
    def __leafinvalidate__(self):
        # request future access to leaf to update the tree
        self._path_ = []
    def __leafisvalid__(self):
        return len(self._path_)>0 if self._path_ is not None else False
    def __leafintree__(self,tree=None):
        # test if self is attached to tree
        if tree is None:
            tree = self._many_
        found = False;
        for leaf in tree:
            if leaf.id == self.id and leaf.parentid == self.parentid:
                # TODO: Look at sheetid as well, if possible
                return tree == self._many_
        return False;
    def __treetraverse__(self,tree,debug=False):
        # update the tree and leaf paths
        if not self.__leafintree__(tree):
            tree = self.__otmattach__(tree)
        self.__leafinvalidate__()
        leaf_count = len(tree)
        waiting = sorted(tree,key=lambda x:x.id,reverse=True)
        done = []
        treshold = leaf_count * leaf_count
        while len(waiting)>0 and treshold >0:
            if debug:
                print(f'DEBUG: entering loop with {",".join(list(str(x.id) for x in waiting))} / {",".join(list(str(x.id) for x in done))}')
            treshold-=1
            leaf = waiting.pop()
            if debug:
                print(f'DEBUG: searching parent {leaf.parentid} for {leaf.id}')
            if leaf.parentid is None or leaf.parentid == '':
                leaf._path_ = [leaf.id]
                done.append(leaf)
                continue
            parents = list(filter(lambda x:x.id == leaf.parentid,done))
            # DONE: By inserting unique ids we ensure we never choke on duplicates
            if len(parents) > 1:
                print('WARNING: Multiple nodes with same id and class found')
            for p in parents:
                leaf._path_= p._path_.copy()
                leaf._path_.append(leaf.id)
                done.append(leaf)
            if leaf not in done:
                waiting.insert(0,leaf) # push the leaf back into waiting
        if len(waiting) > 0:
            print('WARNING: Some nodes have been misplaced')
            self._many_ = waiting.copy()
        else:
            tree = done.copy()
            self._many_ = tree
        return tree
    def __treecmppath__(self,tree=None,leaf=None):
        # return -2,-1,0,1 for leaf before,on, at or after self path
        if tree is None:
            tree = self._many_
        if leaf is None:
            leaf = tree[0]
        self_path = self.__leafpath__()
        leaf_path = leaf.__leafpath__()
        comp_len  = min(len(self_path),len(leaf_path))
        if len(self_path) > comp_len:
            # leaf is one of my (grand)parents
            return -1
        for i in range(comp_len):
            if self_path[i] > leaf_path[i]:
                # leaf is on a previous branch
                return -2
            if self_path[i] < leaf_path[i]:
                # leaf is on a following branch
                return 1
        # leaf is one of my (grand)childs
        return 0
    def __treesortkey__(self,tree=None,debug=False):
        # provide a list of previous node count
        if tree is None:
            tree = self._many_
        if not self.__leafisvalid__():
            self.__treetraverse__(tree)
        sort_list = [0*i for i in range(len(tree))]
        max_p = 1 # By default we have a root-only tree
        max_v = 0
        for l in tree:
            max_p = max(max_p,len(l._path_))
            if str(l.id).isnumeric():
                max_v = max(max_v,int(l.id))
            else:
                print(f'WARNING: Attempted to process non-numeric id: {l.id}')
        if debug:
            print(f'DEBUG: Detected max id: {max_v} and max path: {max_p}')
        scale_factor = 10
        while(max_v>10):
            scale_factor*=10
            max_v/=10
        if debug:
            print(f'DEBUG: Calculated scale factor: {scale_factor}')
        idx = 0
        for l in tree: # second pass
            for i in range(max_p):
                sort_list[idx]*=scale_factor
                if i<len(l._path_):
                    sort_list[idx]+=int(l._path_[i])
            if debug:
                print(f'DEBUG: Generated sort key {sort_list[idx]}')
            idx+=1
        return sort_list
    def __treesort__(self,tree=None):
        # generate a sorted tree
        if tree is None:
            tree = self._many_
        sort_list = self.__treesortkey__(tree)
        return sorted(tree,key=lambda x:sort_list[tree.index(x)])

# Application domain classes
class FMEA_Function(TreeLeaf):
    title = ''                  # The short text presented in the tree
    description = ''            # The longer description of the node
    sheet_author = ''           # Record of the author of the sheet
    sheet_created = ''          # Date of creation for the sheet
    asset_name = ''             # The asset name
    asset_description = ''      # The asset description
    asset_criticality = ''      # The asset criticality category
    # NOTE: difference between sheet is function is that sheet.parentid is None
    def __init__(self):
        self.__doc__ = 'FMEA Function: Class that holds Sheet and Function information'
        self.parentclass = self.__class__.__name__
        # this part of the tree is self contained
    def create_in_db(self,cursor):
        # test the create the table and the initial records
        try:
            table = self.__sqlitetable__()
            transaction = f'''
    BEGIN TRANSACTION;
    DROP TABLE IF EXISTS {table};
    {self.__sqlitecreate__(cursor)};
    CREATE UNIQUE INDEX only_one_id_on_{table} ON {table} (id);
    COMMIT;
            '''
            cursor = cursor.executescript(transaction)
        except Exception as e:
            print(f'ERROR: {e.__class__.__name__} - {e.args} ')
        finally:
            return cursor
    def get_from_db(self,cursor,sheetid=None,tree=None):
        # fill the tree from database (all sheets and functions)
        if tree is None:
            tree = self._many_
        if sheetid is None:
            res = self.__sqlitenext__(cursor,extra_where='parentid IS NULL')
        else:
            if self.id is None:
                # we have an empty tree
                res = self.__sqlitenext__(cursor,extra_where= \
                f'( id = {sheetid} OR parentid = {sheetid} )')
            else:
                res = self.__sqliteself__(cursor,extra_where= \
                f'( id = {sheetid} OR parentid = {sheetid} )')
        if res is not None:
            # we actually got data into self
            found = False
            try:
                idx = tree.index(self) # this can throw not found
            except:
                for leaf in tree:
                    if leaf.id==self.id and type(leaf)==type(self):
                        leaf = self
                        found = True
                        break
            else:
                tree[idx]=self
                found = True
            finally:
                if not found:
                    self.__otmattach__(tree)
            last_id = self.id
            while res is not None:
                anew = self.__class__()
                cursor = res
                if sheetid is None:
                    res = anew.__sqlitenext__(cursor,extra_where=\
                        f'(parentid IS NULL AND id > {last_id})')
                else:
                    res = anew.__sqlitenext__(cursor,extra_where= \
                    f'( (id = {sheetid} OR parentid = {sheetid}) AND id > {last_id}  )')
                if anew.id is None:
                    break
                last_id = anew.id
                if anew.id != self.id and anew.id is not None:
                    found = False
                    for leaf in tree:
                        if leaf.id == anew.id and type(leaf) == type(anew):
                            leaf = anew
                            found = True
                            break
                    if not found:
                        anew.__otmattach__(tree)
        else:
            print('WARNING: Returning the tree unchanged from db')
        return tree
    def init_tree(self,tree=[]):
        # transient function to initialise once the tree
        self.__otmattach__(tree)
        return self
    def populate_from_form(self,formdata,tree=None,with_parentclass=False):
        # take a dict from formdata and updates self
        # looks up the tree and replace/append the leaf
        if tree is None:
            tree = self._many_
        self.__nodeinband__(formdata)
        found = False
        for leaf in tree:
            if leaf.id == self.parentid and with_parentclass:
                self.parentclass = leaf.__class__.__name__
            if leaf.id == self.id and leaf.__nodename__() == self.__nodename__():
                # we didn't compare for parentclass because that can change
                leaf = self
                found = True
        if not found:
            tree = self.__otmattach__(tree)
        return tree
    def update_leaf(self,cursor,tree=None,with_parentclass=False):
        # update the db with the changes into the tree
        if tree is None:
            tree = self._many_
        cursor = self.__sqliteupdate__(cursor)
        # we need to ensure whatever we did to the node is reflected in the tree
        found = False
        for leaf in tree:
            if leaf.id == self.parentid and with_parentclass:
                self.parentclass = leaf.__class__.__name__
            if leaf.id == self.id and leaf.__nodename__() == self.__nodename__():
                # we didn't compare for parentclass because that can change
                leaf = self
                found = True
        if not found:
            tree = self.__otmattach__(tree)
        return tree
    def delete_leaf(self,cursor,tree=None,actions=[]):
        # remove from db a leaf and is's children
        if tree is None:
            tree = self._many_
        parentlist = []
        for leaf in list(filter(lambda x:self.__treecmppath__(tree,x)==0,tree)):
            leaf.__sqlitedelself__(cursor)
            cursor.connection.commit()
            tree.remove(leaf)
            if type(leaf)!=type(self):
                parentlist.append(leaf.id)
        # TODO: Fix delete actions
        #if len(actions)>0 and len(parentlist)>0:
        #    actions[0].__class__().del_action(cursor,parentlist,actions)
        return tree


class FMEA_Failure_Mode(TreeLeaf):
    title = ''                  # The short text presented in the tree
    description = ''            # The longer description of the failure mode
    cause = ''                  # The detailed cause
    risk_level = ''             # The risk level
    discipline = ''             # The discipline applied
    means_of_identification = ''# Means of identification of the failure mode
    sheetid = 0                 #
    def __init__(self):
        self.__doc__ = 'FMEA Failure Mode: Class that holds Failure Causes'
    def create_in_db(self,cursor):
        # create the table and the initial records
        try:
            table = self.__sqlitetable__()
            transaction = f'''
    BEGIN TRANSACTION;
    DROP TABLE IF EXISTS {table};
    {self.__sqlitecreate__(cursor)};
    CREATE UNIQUE INDEX only_one_id_on_{table} ON {table} (id);
    COMMIT; '''
            cursor = cursor.executescript(transaction)
        except Exception as e:
            print(f'ERROR: {e.__class__.__name__} - {e.args} ')
        finally:
            return cursor
    def get_from_db(self,cursor,sheetid=None,tree=None):
        # fill the tree from database (all sheets and functions)
        if tree is None:
            tree = self._many_
        qe = ''
        if sheetid is None:
            sheet = list(filter(lambda x:x.parentid is None, tree))
            if len(sheet)>0:
                sheetid = sheet[0]['id']
                if type(sheetid)==type(int) or type(sheetid)==type(str):
                    qe = f' sheetid = {sheetid} '
        else:
            qe = f' sheetid = {sheetid} '
        if self.id is None:
            # we are at first node in Failure Mode
            res = self.__sqlitenext__(cursor, extra_where = qe)
        else:
            res = self.__sqliteself__(cursor, extra_where = qe)
        if res is not None:
            found = False
            try:
                idx = tree.index(self) # this can throw not found
            except:
                for leaf in tree:
                    if leaf.id==self.id and\
                        type(leaf)==type(self):
                        leaf = self
                        found = True
                        break
            else:
                tree[idx]=self
                found = True
            finally:
                if not found:
                    self.__otmattach__(tree)
            last_id = self.id
            while res is not None:
                anew = self.__class__()
                cursor = res
                if len(qe)>0:
                    res = anew.__sqlitenext__(cursor,extra_where = \
                f'({qe} AND id > {last_id})')
                else:
                    res = anew.__sqlitenext__(cursor,extra_where = \
                f'id > {last_id}')
                if anew.id is None:
                    break
                last_id = anew.id
                if anew.id != self.id and anew.id is not None:
                    found = False
                    for leaf in tree:
                        if leaf.id == anew.id and\
                           type(leaf) == type(anew):
                            leaf = anew
                            found = True
                            break
                    if not found:
                        anew.__otmattach__(tree)
        else:
            print('WARNING: Returning the tree unchanged from db')
        return tree
    def update_leaf(self,cursor,tree=None,with_parentclass=False):
        # update the db with the changes into the tree
        if tree is None:
            tree = self._many_
        # we need to ensure whatever we did to the node is reflected in the tree
        found = False
        for leaf in tree:
            if leaf.id == self.parentid and with_parentclass:
                self.parentclass = leaf.__class__.__name__
            if leaf.id == self.id and leaf.__nodename__() == self.__nodename__():
                # we didn't compare for parentclass because that can change
                leaf = self
        if not found:
            tree = self.__otmattach__(tree)
        # also make sure we have db synched
        cursor = self.__sqliteupdate__(cursor)
        return tree
    def delete_leaf(self,cursor,tree=None,actions=[]):
        # remove from db a leaf and is's children
        if tree is None:
            tree = self._many_
        parentlist=[]
        for leaf in list(filter(lambda x:self.__treecmppath__(tree,x)==0,tree)):
            leaf.__sqlitedelself__(cursor)
            cursor.connection.commit()
            parentlist.append(leaf.id)
            tree.remove(leaf)
        if len(actions)>0:
            actions[0].__class__().del_action(cursor,parentlist,actions)
        return tree

class FMEA_Action(ManyToMany):
    title = ''                  # The short text presented in action list
    description = ''            # The longer description of the action
    category = ''               # The action category
    templating_group = ''       # Data to allow action search
    templating_equipment = ''   # Data to allow action search
    frequency_for_A_criticality = ''
    frequency_for_B_criticality = ''
    frequency_for_C_criticality = ''
    frequency_for_D_criticality = ''
    def __init__(self):
        self.__doc__ = 'FMEA Action: Class that holds Actions applicable'
        self.parentclass = FMEA_Failure_Mode().__class__.__name__
    def create_in_db(self,cursor):
        # create the table and the initial records
        try:
            table = self.__sqlitetable__()
            transaction = f'''
    BEGIN TRANSACTION;
    DROP TABLE IF EXISTS {table};
    {self.__sqlitecreate__(cursor)};
    CREATE UNIQUE INDEX only_one_id_on_{table} ON {table} (id);
    COMMIT; '''
            cursor = cursor.executescript(transaction)
        except Exception as e:
            print(f'ERROR: {e.__class__.__name__} - {e.args} ')
        finally:
            return cursor
    def get_from_db(self,cursor,tree,actions=None):
        # fill the actions from database
        if actions is None:
            actions = self._many_
        relevant_ids = ', '.join(str(z) for z in list(map(lambda x:x.id,\
         list(filter(lambda y:y.__contains__('sheetid'),tree)))))
        qe = f'parentlist IS NOT NULL'
        if self.id is None:
            res = self.__sqlitenext__(cursor, extra_where = qe)
        else:
            res = self.__sqliteself__(cursor, extra_where = qe)
        if res is not None:
            found = False
            try:
                idx = actions.index(self)
            except:
                for act in actions:
                    if act.id == self.id:
                        act = self
                        found = True
                        break # out of for loop
            else:
                actions[idx] = self
                found = True
            finally:
                if not found:
                    self.__mtmattach__(actions)
            prev_id = self.id
            while res is not None:
                anew = self.__class__()
                cursor = res
                res = anew.__sqlitenext__(cursor, extra_where = \
                 f'({qe} and id > {prev_id})')
                if anew.id is None:
                    return actions
                if anew.id != self.id and anew.id is not None:
                    prev_id = anew.id
                    found = False
                    for act in actions:
                        if act.id == anew.id:
                            act = anew
                            found = True
                            break
                    if not found:
                        anew.__mtmattach__(actions)
        else:
            print('WARNING: Returning actions unchanged')
        return actions
    def update_action(self,cursor,actions=None):
        # update the db with the changes into the tree
        if actions is None:
            actions = self._many_
        res = self.__sqliteupdate__(cursor)
        # we need to ensure whatever we did to the node is reflected in the list
        if res is not None:
            found = False
            for act in actions:
                if act.id == self.id:
                    leaf = self
            if not found:
                actions = self.__mtmattach__(actions)
        return actions
    def del_action(self,cursor,parentid=[],actions=None,debug=True):
        # remove from db a leaf and is's children
        # TODO: This is horribly inefficient, try something better
        if debug: print(f'DEBUG: Enter delete with {str(self)}, parents "{parentid}" and actions "{str(a)+" " for a in actions}"')
        if actions is None:
            actions = self._many_
        if actions is None:
            actions = [self]
            self._many_ = actions
        changed = False
        if len(parentid) > 0:
            # we clean the parentlists
            for act in actions:
                if debug: print(f'DEBUG: Evaluating action {str(act)}')
                act_changed = False
                for pid in parentid:
                    if debug: print(f'DEBUG: Evaluating "{pid}" to remove from "{act.parentlist}"')
                    prev_parentlist = act.parentlist
                    new_parentlist = ",".join(list(set(map(lambda z:str(z), filter( \
                     lambda x: x not in parentid and str(x) not in parentid, list(\
                     map(lambda y: int(y.strip()) if y.strip().isnumeric() else -1,\
                     prev_parentlist.split(","))))))))
                    #new_parentlist = act.__mtmdelparent__(pid)
                    if debug: print(f'DEBUG: New parentlist {new_parentlist}')
                    if new_parentlist == '' or new_parentlist is None:
                        if debug: print('DEBUG: Reached delete from db')
                        act.__sqlitedelself__(cursor)
                        actions.remove(act)
                        act_changed = False # we no longer need it
                        break
                    if new_parentlist != prev_parentlist:
                        if debug: print('DEBUG: We note an update')
                        act.parentlist = new_parentlist
                        act_changed = True
                if act_changed:
                    act.__sqliteupdate__(cursor)
        else:
            # we just remove the action
            self.__sqlitedelself__(cursor)
            cursor.connection.commit()
            actions.remove(self)
        return actions
    def add_action(self,cursor,leaf,actions=None):
        # append leaf id into actions
        if actions is None:
            actions = self._many_
        prev_parentlist = self.parentlist
        new_parentlist = self.__mtmaddparent__(leaf.id)
        if new_parentlist != prev_parentlist:
            self.__sqliteupdate__(cursor)

class FMEA_Domain(OneToMany):
    title = ''                  # The short rule description
    table_name = ''             # The table the rule applies to
    field_name = ''             # The field the rule applies to
    field_type = ''             # The input rule (textbox/hidden/text)
    field_option = ''           # The option thdeis rule adds to field
    field_option_color = ''     # The CSS color this option adds
    field_hint = ''             # The hint for tooltips or edit placeholder
    field_o_num = 0             # The display order of the field
    def __init__(self):
        self.__doc__ = 'FMEA Domain: Class that holds all business rules'
    def create_in_db(self,cursor,defaults=True):
        # create the table and the initial records
        try:
            if defaults:
                transaction = f'''BEGIN TRANSACTION;
    DROP TABLE IF EXISTS {self.__sqlitetable__()};
    {self.__sqlitecreate__(cursor)};
    CREATE UNIQUE INDEX only_one_id_on_{self.__sqlitetable__()} ON {self.__sqlitetable__()} (id);
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES (NULL,'id',0,NULL,NULL,'readonly',7,NULL,NULL,'fmea_function','Sheet id');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES (NULL,'parentclass',0,NULL,NULL,'hidden',9,NULL,NULL,'fmea_function','Sheet parent class should be None');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('New Sheet...','title',1,NULL,NULL,'text',14,NULL,NULL,'fmea_function','Sheet title');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Description of the sheet','description',2,NULL,NULL,'longdesc',82,NULL,NULL,'fmea_function','Sheet description');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Created by...','sheet_author',3,NULL,NULL,'text',12,NULL,NULL,'fmea_function', 'Author');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES (NULL,'sheet_created',4,NULL,NULL,'date',13,NULL,NULL,'fmea_function','Created date');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Enter asset name...','asset_name',5,NULL,NULL,'text',6,NULL,NULL,'fmea_function', 'Asset name');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Enter criticality score...','asset_criticality',6,'A','#ff0115','enum',1,NULL,NULL,'fmea_function','Criticality score A - critical');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Enter criticality score...','asset_criticality',6,'B','#dea105','enum',2,NULL,NULL,'fmea_function','Criticality score B - strategic');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Enter criticality score...','asset_criticality',6,'C','#cccc0c','enum',3,NULL,NULL,'fmea_function','Criticality score C - specific');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Enter criticality score...','asset_criticality',6,'D','#20ff35','enum',4,NULL,NULL,'fmea_function','Criticality score D - regular');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Enter asset description...','asset_description',7,NULL,NULL,'longdesc',5,NULL,NULL,'fmea_function','Asset long description');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES (NULL,'id',0,NULL,NULL,'readonly',8,'fmea_function',NULL,'fmea_function','Function id');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES (NULL,'parentclass',0,NULL,NULL,'hidden',10,'fmea_function',NULL,'fmea_function', 'Function parent class should be Sheet');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES (NULL,'parentid',1,NULL,NULL,'readonly',11,'fmea_function',NULL,'fmea_function', 'Function parent id is Sheet');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('New Function...','title',2,NULL,NULL,'text',15,'fmea_function',NULL,'fmea_function','Function title');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Description of the function','description',3,NULL,NULL,'longdesc',83,'fmea_function',NULL,'fmea_function','Function description');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES (NULL,'id',0,NULL,NULL,'readonly',24,'fmea_failure_mode',NULL,'fmea_failure_mode', 'Failure cause id');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES (NULL,'parentclass',0,NULL,NULL,'hidden',26,'fmea_failure_mode',NULL, 'fmea_failure_mode', 'Failure parent class');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES (NULL,'parentid',1,NULL,NULL,'readonly',27,'fmea_failure_mode',NULL, 'fmea_failure_mode', 'Failure cause parent id');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES (NULL,'sheetid',1,NULL,NULL,'hidden',28,'fmea_failure_mode',NULL, 'fmea_failure_mode', 'Failure cause');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('New Failure Mode...','title',2,NULL,NULL,'text',29, 'fmea_failure_mode', NULL, 'fmea_failure_mode', 'Failure Cause Title');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Description of the failure mode','description',3,NULL,NULL,'longdesc',17, 'fmea_failure_mode', NULL, 'fmea_failure_mode', 'Failure Desc');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Enter cause...','disabled_cause',4,NULL,NULL,'text',16,'disabled_fmea_failure_mode',NULL,'disabled_fmea_failure_mode', 'Failure cause');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Define risk level...','risk_level',5,'1','','text',84,'fmea_failure_mode',NULL,'fmea_failure_mode', 'Failure risk level');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Define risk level...','risk_level',5,'2','','text',85,'fmea_failure_mode',NULL,'fmea_failure_mode', 'Failure risk level');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Define risk level...','risk_level',5,'3','','text',86,'fmea_failure_mode',NULL,'fmea_failure_mode', 'Failure risk level');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Define risk level...','risk_level',5,'4','','text',87,'fmea_failure_mode',NULL,'fmea_failure_mode', 'Failure risk level');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Define risk level...','risk_level',5,'6','','text',88,'fmea_failure_mode',NULL,'fmea_failure_mode', 'Failure risk level');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Define risk level...','risk_level',5,'8','','text',89,'fmea_failure_mode',NULL,'fmea_failure_mode', 'Failure risk level');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Define risk level...','risk_level',5,'9','','text',90,'fmea_failure_mode',NULL,'fmea_failure_mode', 'Failure risk level');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Define risk level...','risk_level',5,'12','','text',91,'fmea_failure_mode',NULL,'fmea_failure_mode', 'Failure risk level');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Define risk level...','risk_level',5,'16','','text',92,'fmea_failure_mode',NULL,'fmea_failure_mode', 'Failure risk level');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Applies to discipline...','discipline',6,'Others',NULL,'text',18, 'fmea_failure_mode',NULL,'fmea_failure_mode','Failure discipline');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Applies to discipline...','discipline',6,'Rotating',NULL,'text',19,'fmea_failure_mode',NULL, 'fmea_failure_mode', 'Failure discipline - rotating');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Applies to discipline...','discipline',6,'Fixed',NULL,'text',20, 'fmea_failure_mode' ,NULL, 'fmea_failure_mode', 'Failure discipline - fixed');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Applies to discipline...','discipline',6,'Instrumentation',NULL,'text',21,'fmea_failure_mode', NULL,'fmea_failure_mode', 'Failure discipline - instrumentation');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Applies to discipline...','discipline',6,'Electrical',NULL,'text',22,'fmea_failure_mode',NULL, 'fmea_failure_mode', 'Failure discipline - electrical');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Applies to discipline...','discipline',6,'Process',NULL,'text',23, 'fmea_failure_mode' ,NULL, 'fmea_failure_mode', 'Failure discipline - process');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Identified by...','means_of_identification',6,NULL,NULL,'text',25, 'fmea_failure_mode', NULL, 'fmea_failure_mode', 'Please describe means of identification...');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES (NULL,'id',0,NULL, NULL,'readonly',75, 'fmea_action', NULL, 'fmea_action', 'Action id');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES (NULL,'parentclass',0,NULL, NULL,'hidden',76, 'fmea_action', NULL, 'fmea_action', 'Action is attached to Failure Mode');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES (NULL,'parentlist',0,NULL, NULL,'hidden',77, 'fmea_action', NULL, 'fmea_action', 'Action parents as a text list');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('New Action...','title',1,NULL, NULL,'text',80, 'fmea_action', NULL, 'fmea_action', 'Action Title');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Description of the action','description',2,NULL, NULL,'longdesc',81, 'fmea_action', NULL, 'fmea_action', 'Action Title');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Select category','category',3,'Advanced monitoring','#836953','enum',30, 'fmea_action', NULL, 'fmea_action', 'Action Category - advanced monitoring');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Select category','category',3,'Operation alarms','#99c5c4','enum',31, 'fmea_action', NULL, 'fmea_action', 'Action Category - operation alarms');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Select category','category',3,'Design Upgrade','#b39eb5','enum',32, 'fmea_action', NULL, 'fmea_action', 'Action Category - design upgrade');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Select category','category',3,'Asset Strategies','#befd73','enum',33, 'fmea_action', NULL, 'fmea_action', 'Action Category - asset strategies');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Select category','category',3,'Other Actions','#ff9899','enum',34, 'fmea_action', NULL, 'fmea_action', 'Action Category');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Frequency for critical...','frequency_for_A_criticality',4,'Not applicable', NULL,'text',35, 'fmea_action', NULL, 'fmea_action', 'Frequency set 35');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Frequency for critical...','frequency_for_A_criticality',4,'On demand', NULL,'text',36, 'fmea_action', NULL, 'fmea_action', 'Frequency set 36');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Frequency for critical...','frequency_for_A_criticality',4,'Every shift', NULL,'text',37, 'fmea_action', NULL, 'fmea_action', 'Frequency set 37');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Frequency for critical...','frequency_for_A_criticality',4,'Every turnaround', NULL,'text',38, 'fmea_action', NULL, 'fmea_action', 'Frequency set 38');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Frequency for critical...','frequency_for_A_criticality',4,'Every week', NULL,'text',39, 'fmea_action', NULL, 'fmea_action', 'Frequency set 39');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Frequency for critical...','frequency_for_A_criticality',4,'Twice a month', NULL,'text',40, 'fmea_action', NULL, 'fmea_action', 'Frequency set 40');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Frequency for critical...','frequency_for_A_criticality',4,'Every month', NULL,'text',41, 'fmea_action', NULL, 'fmea_action', 'Frequency set 41');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Frequency for critical...','frequency_for_A_criticality',4,'Every quarter', NULL,'text',42, 'fmea_action', NULL, 'fmea_action', 'Frequency set 42');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Frequency for critical...','frequency_for_A_criticality',4,'Every semester', NULL,'text',43, 'fmea_action', NULL, 'fmea_action', 'Frequency set 43');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Frequency for critical...','frequency_for_A_criticality',4,'Every year', NULL,'text',44, 'fmea_action', NULL, 'fmea_action', 'Frequency set 44');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Frequency for high...','frequency_for_B_criticality',5,'Not applicable', NULL,'text',45, 'fmea_action', NULL, 'fmea_action', 'Frequency set 45');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Frequency for high...','frequency_for_B_criticality',5,'On demand', NULL,'text',46, 'fmea_action', NULL, 'fmea_action', 'Frequency set 46');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Frequency for high...','frequency_for_B_criticality',5,'Every shift', NULL,'text',47, 'fmea_action', NULL, 'fmea_action', 'Frequency set 47');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Frequency for high...','frequency_for_B_criticality',5,'Every turnaround', NULL,'text',48, 'fmea_action', NULL, 'fmea_action', 'Frequency set 48');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Frequency for high...','frequency_for_B_criticality',5,'Every week', NULL,'text',49, 'fmea_action', NULL, 'fmea_action', 'Frequency set 49');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Frequency for high...','frequency_for_B_criticality',5,'Twice a month', NULL,'text',50, 'fmea_action', NULL, 'fmea_action', 'Frequency set 50');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Frequency for high...','frequency_for_B_criticality',5,'Every month', NULL,'text',51, 'fmea_action', NULL, 'fmea_action', 'Frequency set 51');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Frequency for high...','frequency_for_B_criticality',5,'Every quarter', NULL,'text',52, 'fmea_action', NULL, 'fmea_action', 'Frequency set 52');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Frequency for high...','frequency_for_B_criticality',5,'Every semester', NULL,'text',53, 'fmea_action', NULL, 'fmea_action', 'Frequency set 53');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Frequency for high...','frequency_for_B_criticality',5,'Every year', NULL,'text',54, 'fmea_action', NULL, 'fmea_action', 'Frequency set 54');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Frequency for medium...','frequency_for_C_criticality',6,'Not applicable', NULL,'text',55, 'fmea_action', NULL, 'fmea_action', 'Frequency set 55');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Frequency for medium...','frequency_for_C_criticality',6,'On demand', NULL,'text',56, 'fmea_action', NULL, 'fmea_action', 'Frequency set 56');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Frequency for medium...','frequency_for_C_criticality',6,'Every shift', NULL,'text',57, 'fmea_action', NULL, 'fmea_action', 'Frequency set 57');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Frequency for medium...','frequency_for_C_criticality',6,'Every turnaround', NULL,'text',58, 'fmea_action', NULL, 'fmea_action', 'Frequency set 58');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Frequency for medium...','frequency_for_C_criticality',6,'Every week', NULL,'text',59, 'fmea_action', NULL, 'fmea_action', 'Frequency set 59');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Frequency for medium...','frequency_for_C_criticality',6,'Twice a month', NULL,'text',60, 'fmea_action', NULL, 'fmea_action', 'Frequency set 60');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Frequency for medium...','frequency_for_C_criticality',6,'Every month', NULL,'text',61, 'fmea_action', NULL, 'fmea_action', 'Frequency set 61');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Frequency for medium...','frequency_for_C_criticality',6,'Every quarter', NULL,'text',62, 'fmea_action', NULL, 'fmea_action', 'Frequency set 62');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Frequency for medium...','frequency_for_C_criticality',6,'Every semester', NULL,'text',63, 'fmea_action', NULL, 'fmea_action', 'Frequency set 63');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Frequency for medium...','frequency_for_C_criticality',6,'Every year', NULL,'text',64, 'fmea_action', NULL, 'fmea_action', 'Frequency set 64');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Frequency for low...','frequency_for_D_criticality',7,'Not applicable', NULL,'text',65, 'fmea_action', NULL, 'fmea_action', 'Frequency set 65');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Frequency for low...','frequency_for_D_criticality',7,'On demand', NULL,'text',66, 'fmea_action', NULL, 'fmea_action', 'Frequency set 66');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Frequency for low...','frequency_for_D_criticality',7,'Every shift', NULL,'text',67, 'fmea_action', NULL, 'fmea_action', 'Frequency set 67');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Frequency for low...','frequency_for_D_criticality',7,'Every turnaround', NULL,'text',68, 'fmea_action', NULL, 'fmea_action', 'Frequency set 68');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Frequency for low...','frequency_for_D_criticality',7,'Every week', NULL,'text',69, 'fmea_action', NULL, 'fmea_action', 'Frequency set 69');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Frequency for low...','frequency_for_D_criticality',7,'Twice a month', NULL,'text',70, 'fmea_action', NULL, 'fmea_action', 'Frequency set 70');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Frequency for low...','frequency_for_D_criticality',7,'Every month', NULL,'text',71, 'fmea_action', NULL, 'fmea_action', 'Frequency set 71');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Frequency for low...','frequency_for_D_criticality',7,'Every quarter', NULL,'text',72, 'fmea_action', NULL, 'fmea_action', 'Frequency set 72');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Frequency for low...','frequency_for_D_criticality',7,'Every semester', NULL,'text',73, 'fmea_action', NULL, 'fmea_action', 'Frequency set 73');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Frequency for low...','frequency_for_D_criticality',7,'Every year', NULL,'text',74, 'fmea_action', NULL, 'fmea_action', 'Frequency set 74');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Action applies to equipment type...','templating_equipment',8,NULL, NULL,'text',78, 'fmea_action', NULL, 'fmea_action', 'Action Templates - equipment');
    REPLACE INTO {self.__sqlitetable__()}({self.__sqlitefields__()}) VALUES ('Action grouping...','templating_group',9,NULL, NULL,'text',79, 'fmea_action', NULL, 'fmea_action', 'Action Templates - group');
    COMMIT;'''
                print(transaction)
                cursor = cursor.executescript(transaction)
            else:
                print(f'NOTICE: Just creating the {self.__sqlitetable__()} table...')
                cursor = cursor.execute(self.__sqlitecreate__(cursor))
        except Exception as e:
            print(f'ERROR: {e.__class__.__name__} - {e.args} ')
        finally:
            return cursor
    def get_from_db(self,cursor,domain=None):
        # fill the tree from database (all sheets and functions)
        if domain is None:
            domain = self._many_
        if self.id is None:
            res = self.__sqlitenext__(cursor)
        else:
            res = self.__sqliteself__(cursor)
        if res is not None:
            found = False
            try:
                idx = domain.index(self)
            except:
                for d in domain:
                    if d.id == self.id:
                        d = self
                        found = True
                        break
            else:
                domain[idx]=self
                found = True
            if not found:
                self.__otmattach__(domain)
            prev_id = self.id
            while res is not None:
                cursor = res
                anew = self.__class__()
                res = anew.__sqlitenext__(cursor,extra_where=f'id > {prev_id}')
                if anew.id != self.id and anew.id is not None:
                    found = False
                    for d in domain:
                        if d.id == anew.id:
                            d = anew
                            found= True
                            break
                    if not found:
                        anew.__otmattach__(domain)
                prev_id = anew.id
        return sorted(domain,key=lambda x:x.field_o_num)
    def update_leaf(self,cursor,domain=None):
        # update the db with the changes into the tree
        if domain is None:
            domain = self._many_
        res = self.__sqliteupdate__(cursor)
        if res is not None:
            found = False
            for d in domain:
                if d.id == self.id:
                    d = self
                    found = True
                    break
            if not found:
                self.__otmattach__(domain)
        return domain
    def delete_leaf(self,cursor,domain=None):
        # remove from db a rule
        if domain is None:
            domain = self._many_
        res = self.__sqlitedelself__(cursor)
        if res is not None:
            domain = list(filter(lambda x:x.id != self.id,domain))
        return domain
    def get_options(self,leaf,fieldname,domain=None):
        # get the list of options for a field
        if domain is None:
            domain = self._many_
        return list(filter(lambda x: x.fieldname == fieldame and\
                                     x.tablename == leaf.__sqlitetable__(),domain))


class FMEA_App(AttrAccess):
    use_debug            = True # change this when going to prod
    use_import_to_global = True # WARNING: Danger of refactoring
    dependencies = [('flask','Flask','Flask'),('flask','render_template','rend'),('flask','render_template_string','rends'),('flask','redirect','redir'),('flask','url_for','url_for'),('flask','request','request'),('flask','send_file','send_file'),('markupsafe','Markup','Markup'),('os','path','path'),('os','makedirs','mkdir'),('os','remove','rmfile'),('sqlite3','',''),('pandas','','pd'),('openpyxl','','')]
    #from {1} import {2} as {3}
    def __init__(self,app=None):
        self.__doc__ = 'Failure Mode and Effects Analysis: The Flask App'
        if app is not None:
            self.__setattr__('app',app)
    def try_imports(self,to_global=False,debug=False):
        # import needed modules
        # turn dependencies into imported classes/functions/modules
        import importlib,subprocess,sys
        retry = True
        while retry:
            retry = False
            for import_record in self.dependencies:
                from_module = import_record[0]
                import_item = import_record[1]
                import_as   = import_record[2]
                try:
                    if to_global == True:
                        target = globals()
                    else:
                        target = self
                    if import_as == ''   or import_as == '*':
                        import_as = from_module
                    if import_item == '' or import_item == '*':
                        if debug: print(f'NOTICE: Importing from \"{from_module}\" as \"{import_as}\"')
                        target[import_as] = importlib.import_module(from_module)
                        self[import_as]   = target[import_as]
                    else:
                        module = importlib.import_module(from_module)
                        if import_as == from_module:
                            if debug: print(f'NOTICE: Importing from \"{from_module}\" the item \"{import_item}\"')
                            target[import_name] = module.__getattribute__(import_item)
                            self[import_name]   = target[import_name]
                        else:
                            if debug: print(f'NOTICE: Importing from \"{from_module}\" the item \"{import_item}\" as \"{import_as}\"')
                            target[import_as] = module.__getattribute__(import_item)
                            self[import_as]   = target[import_as]
                except Exception as e:
                    print(f'''ERROR: Could not import from "{from_module}" the item "{import_item}" as "{import_as}" because {e.__class__.__name__} saying {e.args}''')
                    try:
                        if sys.executable.lower().find('python')<0:
                            raise Exception("CRITICAL ERROR: Python was not found!")
                        else:
                            subprocess.check_call([sys.executable,"-m","pip","install","--trusted-host","pypi.org","--trusted-host","pypi.python.org","--trusted-host","files.pythonhosted.org`","--default-timeout=1000","--break-system-packages",from_module])
                            retry = True
                    except Exception as e:
                        print(f'ERROR: Could not install module using pip, saying {e.__class__.__name__} - {e.args}')
    def get_secrets(self,password='default'):
        # unscramble some secrets stored in the file
        # TODO: Add cypher here see https://benkurtovic.com/2014/06/01/obfuscating-hello-world.html
        return True
    def get_config(self):
        # get configuration
        # TODO: Use flask app.config for all configuration
        try:
            app = self.__getattribute__('app')
        except:
            script_folder = self.path.dirname(__file__)
            app = self.Flask(__name__)
            self.__setattr__('app',app)
        self.app.config['script_folder'] = self.path.dirname(__file__) # save next to me
        self.app.config['template_folder'] = self.path.join(self.app.config["script_folder"],'static')
        self.app.config['db_file'] = self.path.join(self.app.config["script_folder"],\
         f'{self.__nodename__().lower()}.sqlite3')
        self.app.config['MAX_TREE_DEPTH'] = 15 # Number of Failure Modes
        self.app.config['PREVIEW_LINES']  = 5 # Number of lines in report preview
        self.app.config['MAX_CHARS_DESCRIPTION'] = 20
        #Max number of chars in description preview
    def get_db_connection(self):
        # connect to database
        db_file = self.app.config['db_file']
        # TODO: find a way to cache these
        return self.sqlite3.connect(db_file).cursor()
    def create_default(self,cursor,id,tree):
        FMEA_Function().__nodeinband__({'title': 'Empty FMEA Sheet','id': id,\
        'parentid': None, 'sheet_author':'Anonymous', 'sheet_created': '',\
        'asset_description':'No asset... '}).update_leaf(cursor,tree=tree)
        return tree
    def get_sheets(self,cursor=None):
        # list all sheets in order to select opening
        if cursor is None:
            cursor = self.get_db_connection()
        if FMEA_Function().__sqlitecreate__(cursor) != 'SELECT \"TABLE EXISTS\"':
            self.app_install(cursor)
        sheets = FMEA_Function().get_from_db(cursor,sheetid=None,tree=[])
        if len(sheets)==0: # Nothing in the sheet list
            sheets=self.create_default(cursor,0,sheets)
        return sheets
    def get_sheet_tree(self,cursor=None,id=0):
        # list the sheet tree of functions and failure causes
        if cursor is None:
            cursor = self.get_db_connection()
        if FMEA_Function().__sqlitecreate__(cursor) != 'SELECT \"TABLE EXISTS\"' or\
           FMEA_Failure_Mode().__sqlitecreate__(cursor) != 'SELECT \"TABLE EXISTS\"':
            self.app_install(cursor) # create the database
        tree = FMEA_Function().get_from_db(cursor,id,[])
        tree = FMEA_Failure_Mode().get_from_db(cursor,id,tree)
        if len(tree)==0: # Nothing in the sheet
            tree = self.create_default(cursor,id,tree)
        return tree[0].__treesort__(tree) #prefer it to be pre-sorted
    def get_action_list(self,cursor=None,tree=[]):
        # get the actions, related to a tree
        if cursor is None:
            cursor = self.get_db_connection()
        if FMEA_Action().__sqlitecreate__(cursor) != 'SELECT \"TABLE EXISTS\"':
            # we should never get here!
            self.app_install(cursor)
        return FMEA_Action().get_from_db(cursor,tree,[])
    def get_domain_list(self,cursor=None,for_class=None):
        # get the domain for usage in generation of options and dialogs
        if cursor is None:
            cursor = self.get_db_connection()
        if FMEA_Domain().__sqlitecreate__(cursor) != 'SELECT \"TABLE EXISTS\"':
            # we should never get here!
            self.app_install(cursor)
        # TODO: See if you can cache this into flask app config
        if for_class is None:
            return FMEA_Domain().get_from_db(cursor,[])
        else:
            if type(for_class).__name__.find('FMEA')>=0:
                for_class = for_class.__sqlitetable__()
            else:
                for_class = for_class.lower()
            return list(filter(lambda x:x['table_name']==for_class,\
                FMEA_Domain().get_from_db(cursor,[])))
    def derive_template(self,base='',title='',header='',footer='',\
                        content='',css='',js='',icon=''):
        if header == '':
            header = f'''<a class="a-header-index" href="{self.url_for("fmea_index")}">
            Sheets</a>'''
        if footer == '':
            footer = '''<span> Copyright&copy; <a href="mailto:mihaigabriel.vasile23@gmail.com">
            Mihai-Gabriel Vasile</a>&nbsp;2023</span>'''
        if icon == '':
            icon = 'data:image/x-icon;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAAA5CAYAAACGRC3XAAAA0GVYSWZJSSoACAAAAAoAAAEEAAEAAABAAAAAAQEEAAEAAAA5AAAAAgEDAAMAAACGAAAAEgEDAAEAAAABAAAAGgEFAAEAAACMAAAAGwEFAAEAAACUAAAAKAEDAAEAAAADAAAAMQECAA0AAACcAAAAMgECABQAAACqAAAAaYcEAAEAAAC+AAAAAAAAAAgACAAIAAoAAAABAAAACgAAAAEAAABHSU1QIDIuMTAuMzQAADIwMjM6MDk6MTcgMTU6NTk6NTcAAQABoAMAAQAAAAEAAAAAAAAAlHnM9AAAAYRpQ0NQSUNDIHByb2ZpbGUAAHicfZE9SMNAHMVfU8UPKiJ2EHHIUJ3soiLiVKtQhAqhVmjVweTSL2jSkKS4OAquBQc/FqsOLs66OrgKguAHiKuLk6KLlPi/pNAixoPjfry797h7Bwj1MtOsjhig6baZSsTFTHZV7HpFDwYQwiwEmVnGnCQl4Tu+7hHg612UZ/mf+3P0qTmLAQGROMYM0ybeIJ7etA3O+8RhVpRV4nPicZMuSPzIdcXjN84FlwWeGTbTqXniMLFYaGOljVnR1IiniCOqplO+kPFY5bzFWStXWfOe/IWhnL6yzHWaI0hgEUuQIEJBFSWUYSNKq06KhRTtx338w65fIpdCrhIYORZQgQbZ9YP/we9urfzkhJcUigOdL47zMQp07QKNmuN8HztO4wQIPgNXestfqQMzn6TXWlrkCOjfBi6uW5qyB1zuAENPhmzKrhSkKeTzwPsZfVMWGLwFete83pr7OH0A0tRV8gY4OATGCpS97vPu7vbe/j3T7O8HkFBysq4qbTUAAA14aVRYdFhNTDpjb20uYWRvYmUueG1wAAAAAAA8P3hwYWNrZXQgYmVnaW49Iu+7vyIgaWQ9Ilc1TTBNcENlaGlIenJlU3pOVGN6a2M5ZCI/Pgo8eDp4bXBtZXRhIHhtbG5zOng9ImFkb2JlOm5zOm1ldGEvIiB4OnhtcHRrPSJYTVAgQ29yZSA0LjQuMC1FeGl2MiI+CiA8cmRmOlJERiB4bWxuczpyZGY9Imh0dHA6Ly93d3cudzMub3JnLzE5OTkvMDIvMjItcmRmLXN5bnRheC1ucyMiPgogIDxyZGY6RGVzY3JpcHRpb24gcmRmOmFib3V0PSIiCiAgICB4bWxuczp4bXBNTT0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wL21tLyIKICAgIHhtbG5zOnN0RXZ0PSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvc1R5cGUvUmVzb3VyY2VFdmVudCMiCiAgICB4bWxuczpkYz0iaHR0cDovL3B1cmwub3JnL2RjL2VsZW1lbnRzLzEuMS8iCiAgICB4bWxuczpHSU1QPSJodHRwOi8vd3d3LmdpbXAub3JnL3htcC8iCiAgICB4bWxuczp0aWZmPSJodHRwOi8vbnMuYWRvYmUuY29tL3RpZmYvMS4wLyIKICAgIHhtbG5zOnhtcD0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wLyIKICAgeG1wTU06RG9jdW1lbnRJRD0iZ2ltcDpkb2NpZDpnaW1wOmExMjI1N2YzLTFhY2UtNDgxMC1iNTM3LTc1Mjk0NjViMzE3NyIKICAgeG1wTU06SW5zdGFuY2VJRD0ieG1wLmlpZDo0NjA5YTE2Ny02MDFkLTQ5NTYtYjlkMy0yYmFlODVkYmZlYWIiCiAgIHhtcE1NOk9yaWdpbmFsRG9jdW1lbnRJRD0ieG1wLmRpZDowMDZlMzM2ZC1iMDIwLTRkNjQtOGFmNS0wMTc2Zjk0NzJhN2MiCiAgIGRjOkZvcm1hdD0iaW1hZ2UvcG5nIgogICBHSU1QOkFQST0iMi4wIgogICBHSU1QOlBsYXRmb3JtPSJMaW51eCIKICAgR0lNUDpUaW1lU3RhbXA9IjE2OTQ5NTU2MDI4NTY1MDUiCiAgIEdJTVA6VmVyc2lvbj0iMi4xMC4zNCIKICAgdGlmZjpPcmllbnRhdGlvbj0iMSIKICAgeG1wOkNyZWF0b3JUb29sPSJHSU1QIDIuMTAiCiAgIHhtcDpNZXRhZGF0YURhdGU9IjIwMjM6MDk6MTdUMTU6NTk6NTcrMDM6MDAiCiAgIHhtcDpNb2RpZnlEYXRlPSIyMDIzOjA5OjE3VDE1OjU5OjU3KzAzOjAwIj4KICAgPHhtcE1NOkhpc3Rvcnk+CiAgICA8cmRmOlNlcT4KICAgICA8cmRmOmxpCiAgICAgIHN0RXZ0OmFjdGlvbj0ic2F2ZWQiCiAgICAgIHN0RXZ0OmNoYW5nZWQ9Ii8iCiAgICAgIHN0RXZ0Omluc3RhbmNlSUQ9InhtcC5paWQ6ZDlhMjJkMTEtZGUyOC00ZmJkLWI4M2UtN2U0NzU0ZmI0NzMxIgogICAgICBzdEV2dDpzb2Z0d2FyZUFnZW50PSJHaW1wIDIuMTAgKExpbnV4KSIKICAgICAgc3RFdnQ6d2hlbj0iMjAyMy0wOS0xN1QxNjowMDowMiswMzowMCIvPgogICAgPC9yZGY6U2VxPgogICA8L3htcE1NOkhpc3Rvcnk+CiAgPC9yZGY6RGVzY3JpcHRpb24+CiA8L3JkZjpSREY+CjwveDp4bXBtZXRhPgogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgCjw/eHBhY2tldCBlbmQ9InciPz7aLHOKAAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAAPoAAAD6AG1e1JrAAAAB3RJTUUH5wkRDQACxPYhbgAABilJREFUaN7lWj2TG0UQfT0zK+msO53kKzBVQJEQOMEFFJASOSAkISDjx8C/cUBKQEBEEQABFIk/yuWyoXzG1t3p7vSxO00g7e7s7Mzu7EqysU7RqDW76u5502/29dI3333LuMIf1e108NG7RwAliDXhxeQCQkjs7/UgJDBjgkwYT569wPFktnsJmM3n+Pne31cXAbc/vQkAIMNIYIcNlo2XY/LN44pr0zss5zCbtnzA5jy2fndex4XrMrt1rXk/Op4+4DQY0/lsnAXombP63UxaPm91DZXvy5w7k409NjtRG7GtciDMteYSBhxZt+dwAQ/ZHHaMC9dTGTU+G62+bdS2Mgi/w2TBLCQp9pgKcGYj0TmScmc2YTO/1NmIAFEVYO0q1qDAvQ+p4IA9JgcKaItoEU1h7l1tbyKpGimGM/DA1GXbDILSLcDN9z4jICkhKIADBaG2tRFEaRE0HaYaFPgDZC9SwlGwDpwrEeRBgchWlANWsQXMS0ipQMG6ha4NWoQdIDtgvglahLOg5velV0SLIiTA7dFiec42Cl0VggQaBPg60iJqUCCaraKfFnkLtEgvgRaFkwFa0CK2QIt4CbQouHblX19aDEGQMAMsMMAO0GIIgkRdgLtOi60eh91IaVcvKmlxK+f/ok3U7n1ukhS0rhfBzwmBtBiKIAUGOIMHF57V03EcJzg5Oy8qRZbqA0s56nUiHPT3CgoQUZoUQxkCZal1/TcIIM6vYdNGhv7lsq1WPLVRdt/cptI/Yisz6USA8esfd8FJM7HxyfFzfP3FZ5nb/v8wkrIymEkhW0Viy19aJddloxzBThsA5Vod20mdaBwNDxsl4GRyYQmgKASIAgpQPa5CwTo24hwB9qqzCaGWknOOLj/MASBJNO78+Du6nah0D3LUDLuQaB3jy88/MCC+3NY2WlwIUunXHAUuJyk8aObSGaIO5os4gep08dYb16EiFfxfWi+jefj4aQ5tI/oQFKiCkxUFMf2cTS4RxzGEFIgihcv5AhzHkCrCcNC39PcaaBtbDgC0kbln4wmkFFBSYjZfoCs0ZgkghMDhQR9SuBfFVeiqbMqGvcthAEsnOhG63Qh7vQg6ScBCYrgfgbWGXi4rTsZj9K71M2j/9uf96oYKMz68+R50nGB8do43j4YAgEG/lyGqG/WgBGGPAc0aaezHJ2c47F/L+T2NwSp0PhsIOQLS3Z7CyK4F6f7srCD6YnIBCAGdJDg4OEBHLY8Uw9EoC1VKiU9uvW9RZ7npMp3NIZTE6HA/u7YTKUynl5jHGkkcQyoFZsbhQT7nxmhQlsI4nCoJcBXBYtEhTwEaDQdOCCZag4gKRdXmfZsWnb0uAL3eHnoVNSBJNEiQcw+EUqWCiwEctBj6kUI4mcA5XhmUkljMZ/jn+N/akutiBcnx0t8WtKjqixVh/U/16U9Kia9uf2ydMPPtEtpb9J/8/LSoyhxdpkUhBZ6PzxqFfH45zU9eDU9//q1IhYarq6jBaaugxQcXjwrd4VInmIAkSXB6OikVM3hWJ30W2O/3MmfDOszNutCcPUnWd5h9NuU7/Zm0qKTE9dHAcqyYBJfzRtfe5BnAi4L6euF7Tmhy/jdpUfgfb6kkioTL32GPw+yQz7Bt+cySxQQaBLiWZhAYYFN1KVT/98liIkgQZV9j1PVKy2ZetqjvQdgvW6zTGWoEc6rpFrcRUcO6SlyQz9qLqCZaHLI41aAgPMBmLfQGXSXHfZu2xQ1N0C52Fau4AZgzt0iKR0RFjYgaIqyKugDdsvj6Iiqq5PZNiqg1wqpovPd3jBaFH17htNiqhd6QFnlLtCiarWKDFvqGaREhLNOCFgU7Tn+boMUgh/8HtCjqT3y7TYuiKsCrQIvVL0peAVoUlTDfOC02e9niZdCiCH2jazO0iFdIi+4XK4Sriu4mLcKJAnXn+x9KsqfzO7ncRcC1HDSXCgYO86k09l/HrrYiA+ruwye4yh/V63Vx6+1DaC0gVQKhIixEBH1xifEMeGcQYZokeD6+wI1RH/GCMdXAeaIx6AiQkhggxtPzBWR3D8Mu8NNfj1+fBEynM/xy7ymkkOhIoKskxpfzbMJ9AyB3j093DgH/AUoFKSW6y1w4AAAAAElFTkSuQmCC'
        if base == '':
            return f'''<!doctype html>
            <html>
             <head>
              <title>{title}</title>
              <link rel="shortcut icon" href="{icon}" type="image/x-icon">
              <style type="text/css">{css}</style>
              <script type="text/javascript">{js}</script>
             </head>
             <body onload="FMEA_Init()">
              <header class="header">{header}</header>
              <div class="content">{content}</div>
              <footer class="footer">{footer}</footer>
             </body>
            </html>'''
        else:
            return base.format(title=title,header=header,footer=footer,\
                                content=content,css=css,js=js)
    def derive_headers(self,pagename='index',sheet_id=0):
        # generate function HTML for a page type
        if pagename=='index' or pagename=='open':
            return f'''<div class="hdr-left">
    <a id="hdr-index" class="hdr-la" href="{self.url_for("fmea_index")}">Sheets
    </a>&nbsp;
    <a id="hdr-new" class="hdr-la" href="/fmea/redirect/0/sheetnew" onclik="FMEA_New_Sheet();return false">New</a>&nbsp;
    <a id="hdr-open" class="hdr-la" href="#" onclick="FMEA_sheetOpen();return false">Open</a>&nbsp;
    <div id="hide-open-form" class="right-dlg-hidden">
     <form id="open-form" action="/fmea/redirect/0/uploadsheet" method="POST" enctype="multipart/form-data">
      <input id="open-form-in" name="sheetfile" type="file" style="position:absolute;top:-3000px;display:hide" accept="application/octet-stream,.fmea,.fmeasheet,.sqlite3" onchange="document.getElementById('open-form').submit();"/>
     </form>
    </div></div>
   <div class="hdr-cntr">
  <!--   <a href="#">Three</a>&nbsp;
     <a href="#">Four</a>&nbsp; -->
    </div>
    <div class="hdr-right">
     <a id="hdr-admin" class="hdr-la" href="#">Administration</a>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
    </div>'''
        if pagename=='edit' or pagename=='editor':
            return f'''<div class="hdr-left">
    <a id="hdr-index" class="hdr-la" href="{self.url_for("fmea_index")}">Sheets
    </a>&nbsp;
    <a id="hdr-view" class="hdr-la" href="./apidefault#fmeals-fmeaf-{sheet_id}"
    onclick="navigateAndHighlight('fmeald-fmeaf-{sheet_id}');return false"
    >View tree</a>&nbsp;
    </div>
  <!-- <div class="hdr-cntr">
     <a href="#">Three</a>&nbsp;
     <a href="#">Four</a>&nbsp;
    </div> -->
    <div id="hdr-right" class="hdr-right">
     <a id="hdr-actions" class="hdr-la" href="#" onclick="treeActions('right-dlg','right-dlg-hidden');return false">Actions</a>&nbsp;
     <a id="hdr-export" class="hdr-la" href="/fmea/export/{sheet_id}/apidefault">Export</a>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
    </div>''' # TODO: Fetch action list with AJAX
        if pagename=='export' or pagename=='report':
            return f'''<div class="hdr-left">
    <a id="hdr-index" class="hdr-la" href="{self.url_for("fmea_index")}">Sheets
    </a>&nbsp;
    <a id="hdr-back" class="hdr-la" href="/fmea/edit/{sheet_id}/apidefault">
    Back to tree</a>&nbsp;
    </div>
  <!-- <div class="hdr-cntr">
     <a href="#">Three</a>&nbsp;
     <a href="#">Four</a>&nbsp;
    </div> -->
    <div class="hdr-right">
     <a id="hdr-option" class="hdr-la" href="#">Report options</a>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
    </div>'''
    def derive_leaf(self,leaf,opts='',tree_state=None,leaf_acts=None,leaf_dom=None,\
     debug=False):
        # generate HTML for a leaf, assumes all leafs have title
        # TODO: Keep track of state and turn buttons into toggles
        # TODO: Disable collapses that have no purpose (ie. first/last branch, no children
        extra_class=''
        if leaf.parentid is None:
            extra_class = ' fix-top'
            ls_anchors = '''<a href="#">&nbsp;</a><a href="/fmea" onclick="window.location.assign('/fmea')">&lt;</a>
            <a href="#">&nbsp;</a>'''
            rs_anchors = f'''
    <a href="./apinojs?{opts}act=hic&id={leaf.id}" onclick="treeCollapse({leaf.id},'child');return false">{"&laquo;" if tree_state is not None else "&nbsp;"}</a>
    <a href="./apinojs?{opts}act=add&id={leaf.id}" onclick="leafPrepareEdit({leaf.id},null);return false">&#8862;</a>
    <a href="#">&nbsp;</a>'''
        else:
            ls_anchors = f'''
    <a href="./apinojs?{opts}act=hib&id={leaf.id}" onclick="treeCollapse({leaf.id},'before');return false">{"&darr;" if tree_state is not None else "&nbsp;"}</a>
    <a href="./apinojs?{opts}act=del&id={leaf.id}" onclick="leafPrepareDelete({leaf.id});return false" >&#9746;</a>
    <a href="./apinojs?{opts}act=hia&id={leaf.id}" onclick="treeCollapse({leaf.id},'after');return false">{"&uarr;" if tree_state is not None else "&nbsp;"}</a>
    '''
            rs_anchors = f'''
    <a href="./apinojs?{opts}act=hic&id={leaf.id}" onclick="treeCollapse({leaf.id},'child');return false">{"&laquo;" if tree_state is not None else "&nbsp;"}</a>
    <a href="./apinojs?{opts}act=add&id={leaf.id}" onclick="leafPrepareEdit({leaf.id},null);return false">&#8862;</a>
      <a href="./apinojs?{opts}act=mov&id={leaf.id}" onclick="leafPrepareMove({leaf.id});return false">&hellip;</a>'''
            if len(leaf._path_)-1>=self.app.config['MAX_TREE_DEPTH']:
                if debug:
                    print(f'DEBUG: Found large path {leaf._path_}')
            #else:
                rs_anchors = f'''<a href="#">&nbsp;</a><a href="#">&nbsp;</a>
      <a href="./apinojs?{opts}act=mov&id={leaf.id}" onclick="leafPrepareMove({leaf.id});return false">&hellip;</a>'''
        actml = ''
        if leaf_acts is not None:
            at_most_5 = 5;
            for la in leaf_acts:
                at_most_5-=1
                if at_most_5 == 0: break
                actml = f'''{actml}
    <a href="#" onclick=""'''
        return f'''<div id="{leaf.__htmlid__("fmeald")}" class="leaf{extra_class}"
     data-raw="{str(leaf)}" data-path="{str(leaf._path_)}">
     <div id="{leaf.__htmlid__("fmeall")}" class="leaf-ls">{ls_anchors}
     </div><div id="{leaf.__htmlid__("fmealt")}" class="leaf-title">
      <div id="{leaf.__htmlid__("fmeatt")}" class="leaf-tidiv">
       <a href="./apinojs?{opts}act=edt&id={leaf.id}" onclick="leafPrepareEdit(
       {leaf.parentid if leaf.parentid is not None else 'null'},{leaf.id});return false">
        <span id="{leaf.__htmlid__("fmeati")}" style="text-align:left;font-size:1.8vmin;">
        {leaf.id}{"</span><br/>" if len(leaf.title)>5 else ":</span>"}
        <span id="{leaf.__htmlid__("fmeats")}">{leaf.title if len(leaf.title)>0 else "---"}
        </span></a></div>
      <div id="{leaf.__htmlid__("fmeata")}" class="leaf-ta">
       <span id="{leaf.__htmlid__("fmeats")}">
       {self.derive_action_list(leaf_acts,leaf_dom,tree=[leaf],tiny=True) if leaf_acts is not None else ""}</span>
      </div>
      <div id="{leaf.__htmlid__("fmealh")}" class="leaf-th" style="display:none;">{leaf.description}</div>
     </div><div id="{leaf.__htmlid__("fmealr")}" class="leaf-rs">
      {rs_anchors}
     </div></div>''' # TODO: Implement drag/drop
    def derive_tree(self,tree,tree_query=None,domain=None,actions=None,debug=False):
        # generate the tree HTML
        if len(tree)==0:
            return '<p>No data to display</p>'
        else:
            tree = tree[0].__treesort__(tree)
            if tree_query is not None:
                va = tree_query.get('act',[])
                vi = tree_query.get('id',[])
            if debug:
                print(f'DEBUG: Sorted tree looks like {list(l._path_ for l in tree)}')
        result = ''
        prev_leaf = None
        for leaf in tree:
            if prev_leaf is None:
                # we are dealing with the root node
                result = f'''
                    <ul id="{leaf.__htmlid__("fmeatl")}" class="fmeatl">
                    <li id="{leaf.__htmlid__("fmeatb")}" class="fmeatb" >
                    {self.derive_leaf(leaf)}''' # the root node never has actions
            else:
                leaf_actions = list(filter(lambda x:leaf.id in list(map(lambda y:int(y.strip()) if y.strip().isnumeric() else None,x.parentlist.split(','))),actions))
                if debug: print(f'DEBUG: Found for leaf {leaf.id} actions {leaf_actions}')
                if prev_leaf.id == leaf.parentid:
                    result = f'''{result}
                    <ul id="fmea_tree_lvl_{len(leaf._path_)-1}" class="fmea_tree_lvl">
                    <li id="fmea_tree_br_{leaf.id}" class="fmea_tree_br" >
                    {self.derive_leaf(leaf,leaf_acts=leaf_actions,leaf_dom=domain)}'''
                else:
                    if prev_leaf.parentid == leaf.parentid:
                        result = f'''{result}</li>
                        <li id="fmea_tree_br_{leaf.id}" class="fmea_tree_br" >
                        {self.derive_leaf(leaf,leaf_acts=leaf_actions,leaf_dom=domain)}'''
                    else:
                        repeat_pattern = len(prev_leaf._path_)-len(leaf._path_)
                        result = f'''{result}{"</li></ul>"*repeat_pattern}
                            <li id="fmea_tree_br_{leaf.id}" class="fmea_tree_br" >
                            {self.derive_leaf(leaf,leaf_acts=leaf_actions,leaf_dom=domain)}'''
            prev_leaf = leaf
        for i in range(len(prev_leaf._path_)):
            result = f'{result}'
        return result
    def derive_action_legend(self,domain,tiny=False,debug=True):
        # generate a colored legend for action types
        action_types = list(filter(lambda x:x.table_name == 'fmea_action' and\
         x.field_name == 'category',domain))
        if len(action_types) <= 0:
            return '<div id="act-legend" class="act-legend"><h3>No legend</h3></div>'
        else:
            render_legend='<div id="act-legend" class="act-legend"><h3>Legend</h3>&nbsp;<br/>'
            i = 0
            for at in action_types:
                i+=1
                render_legend= f'''{render_legend}
<div id="leg-{i}" class="action" style="background:{at.field_option_color};font-size:1.5vmin;">{at.field_option}</div>'''
            return f'''{render_legend}<div id="leg-{i+1}" class="action" style="font-size:1.5vmin;">No Category
            </div> </div>'''
    def derive_action_list(self,actions,domain,tree=[],tiny=False,debug=False):
        # generate the action list, search and filter functions
        if len(tree) == 0 and not tiny:
            return '<span>No actions have been added within the sheet</span>'
        if len(tree) == 0 and tiny:
            return '<span>[]</span>'
        search_node = FMEA_Failure_Mode().__nodename__()
        tree_ids = list(map(lambda x:x.id,filter(lambda y:y.__nodename__()==\
            search_node,tree)))
        select_actions = []
        source_actions = actions.copy()
        for id in tree_ids:
            # we want to list actions as sorted by tree path
            for act in source_actions:
                parent_list = act.parentlist.split(',')
                #if debug: print(f'DEBUG: Converted {act.parentlist} into {parent_list}')
                if str(id) in parent_list:
                    select_actions.append(act)
                    #source_actions.remove(act)
        search_table = FMEA_Action().__sqlitetable__()
        render_list = ''
        category_colors = dict(map(lambda v:tuple([v.field_option, \
          v.field_option_color]),filter(lambda x:x.table_name == search_table \
                                         and x.field_name == 'category',domain)))
        if len(tree) == 1:
            parent_id = tree[0].id
        else:
            parent_id = '\'*\''
        if debug: print(f'DEBUG: Selected from {list(f"{a.id}:{a.parentlist} " for a in actions)} just {list(f"{a.id}:{a.parentlist} " for a in select_actions)}')
        at_most_5 = 5
        for ac in select_actions:
            parents = ac.parentlist.split(',')
            parent_lookup = ''
            for p in parents:
                parent_lookup = f'''{parent_lookup}
     <a href="#" onclick="navigateAndHighlight('fmeald-fmeafm-{p.strip()}');return false" >#{p.strip()}</a>&nbsp;'''
            if not tiny:
                render_list = f'''{render_list}
    <div id="{ac.__htmlid__('action')}" class="action" data-raw="{str(ac)}"
     style="background:{category_colors[ac.category] if ac.category!='' else ''};" >
     <a href="#" onclick="actionEdit({ac.id},{parent_id});return false">
     {str(ac.id)+": "+ac.title if not tiny else "#"+str(ac.id)}</a>&nbsp;
     <span class="action-right">{parent_lookup}
     <a href="#" onclick="actionDelete({ac.id},{parent_id});return false">&#9746;</a>
     </span>
    </div>'''
            else:
                at_most_5 -= 1
                if at_most_5 <= 0:
                    if debug: break
                render_list = f'''{render_list}<a href="#" onclick="actionEdit({ac.id},'*'  );return false" data-raw="{str(ac)}" style="font-size:1.5vmin;background:{category_colors[ac.category] if ac.category!='' else ''};">#{ac.id}</a>&nbsp;'''
        return render_list
    def derive_input_field(self,fieldrec,fieldvalue,domain,tree=[]):
        # fieldrec is a triplet of field name, field type, field hint
        # assumes the tree excludes sheet, self and children
        # TODO: Make parentid list from tree
        fieldrecx = fieldrec[0].replace('_','-')
        fieldrect = fieldrec[0].replace('_',' ').capitalize()
        if fieldrect == 'Asset name': fieldrect = 'Asset tag'
        # TODO: Remove this cheat when client has enough data to do damage
        if fieldrect[-2:].lower()=='id':
            fieldrect = f'{fieldrect[:-2]} ID'
        fieldhtml = f'''<div id="edit-d-{fieldrecx}" class="edit-d">
            <label id="edit-lbl-{fieldrecx}" for="edit-in-{fieldrecx}"
         class="edit-lbl">{fieldrect}:</label>&nbsp;'''
        options = list(map(lambda x:tuple([x.field_option,x.field_option_color]),\
         filter(lambda y:y.field_name==fieldrec[0] and y.field_type==fieldrec[1],\
         domain)))
        datalistsp=''
        datalisttext = ''
        if len(options)>1:
            datalistid = f'edit-dl-{fieldrecx}'
            datalistsp = f' list="{datalistid}"'
            if fieldrec[2] is not None:
                if len(fieldrec[2])>0:
                    datalisttext = f'''
    <option value="{fieldrec[2]}" selected disabled hidden>{fieldrec[2]}</option>'''
            for opt in options:
                if opt[0]==fieldvalue:
                    datalisttext = f'''{datalisttext.replace('" selected','"')}
    <option value="{opt[0]}" selected="selected" data-color="{opt[1]}">{opt[0]}</option>'''
                else:
                    datalisttext = f'''{datalisttext}
    <option value="{opt[0]}" data-color="{opt[1]}">{opt[0]}</option>'''
        if fieldrec[1] == 'text' or fieldrec[1] == '':
            if len(datalisttext)>0:
                datalisttext= f'''
    <datalist id="{datalistid}" name="{datalistid}" data-fieldname="{fieldrec[0]}">
    {datalisttext}</datalist>'''
            return f'''{fieldhtml}{datalisttext}
    <input type="text"{datalistsp} name="{fieldrec[0]}" class="edit-in"
    id="edit-in-{fieldrecx}" value="{fieldvalue}" placeholder="{fieldrec[2]}"/></div>'''
        if fieldrec[1] == 'readonly':
            if fieldrec[0] == 'parentid':
                parentopt =''
                for leaf in tree:
                    if leaf.id == fieldvalue:
                        parentopt = f'''{parentopt}
    <option value="{leaf.id}" selected="selected">{leaf.id}</option>'''
                    else:
                        parentopt = f'''{parentopt}
    <option value="{leaf.id}">{leaf.id}</option>'''
                if len(parentopt) == 0:
                    parentopt = f'''
    <option value="{fieldvalue}" selected="selected">{fieldvalue}</option>'''
                return f'''{fieldhtml}<select id="edit-in-{fieldrecx}" name="{fieldrec[0]}"
    value="{fieldvalue}" class="edit-in" readonly="readonly">{parentopt}</select></div>'''
            else:
                return f'''{fieldhtml}<input type="text" name="{fieldrec[0]}" class="edit-in"
            readonly="readonly" id="edit-in-{fieldrecx}" value="{fieldvalue}"
            placeholder="{fieldrec[2]}"/>
    </div>'''
        if fieldrec[1] == 'hidden':
            return f'''<input type="hidden" name="{fieldrec[0]}" class="edit-in-hidden"
            readonly="readonly" id="edit-in-{fieldrecx}" value="{fieldvalue}"
            placeholder="{fieldrec[2]}"/>'''
        if fieldrec[1].find('date')>=0 or fieldrec[1].find('time')>=0:
            return f'''{fieldhtml}<input type="date" name="{fieldrec[0]}"
    id="edit-in-{fieldrecx}" value="{fieldvalue}" class="edit-in"/></div>'''
        if fieldrec[1] == 'longdesc' or fieldrec[1] == 'textbox':
            return f'''{fieldhtml}<br/><textarea rows="3" id="edit-in-{fieldrecx}"
    name="{fieldrec[0]}" class="edit-in-widetext">{fieldvalue}</textarea></div>'''
        if fieldrec[1] == 'enum' or fieldrec[1] == 'select':
            return f'''{fieldhtml}<select id="edit-in-{fieldrecx}" name="{fieldrec[0]}"
    value="{fieldvalue}" class="edit-in">{datalisttext}</select></div>'''
    def derive_leaf_edit(self,cursor,leaf,tree=[]):
        # generate the HTML form to edit a leaf
        domain = self.get_domain_list(cursor)
        formhtml = ''
        print(f'DEBUG: Deriving leaf edit for {str(leaf)}')
        if leaf.__nodename__() == FMEA_Function().__nodename__() and \
           leaf.parentid is None:
            # we are editing the sheet details
            # TODO: Add some data list for asset names
            formhtml = '<p>Sheet</p>'
            leafdom = list(filter(lambda x:x.parentclass=='' or x.parentclass==None,domain))
            print(f'DEBUG: Leafdom Sheet - {str(leafdom)}')
            field_list = []
            # TODO: Ensure that this triplet is unique for every parentclass
            if len(leafdom)==0:
                return f'{formhtml}<br/><p>Domain data for Sheet not found</p>'
            else:
                field_list = list(set(map(lambda x: tuple([x.field_name,\
                            x.field_type,x.field_hint,x.field_o_num]), leafdom)))
                print(f'Sheet field list: {field_list}')
                for field in sorted(field_list,key=lambda f:f[3]):
                    # notice the order in the Domain table matters
                    print(f'''DEBUG: Deriving input field
                    field: {field},value:{leaf[field[0]]}''')
                    formhtml = f'''{formhtml}
            {self.derive_input_field(field,leaf[field[0]],leafdom)}'''
        else:
            if leaf.__nodename__() == FMEA_Function().__nodename__():
                # we are editing a function
                formhtml = '<p>Function</p>'
                leafdom = list(filter(lambda x:x.parentclass==leaf.__nodename__(),domain))
                field_list = []
                # TODO: Ensure that this triplet is unique for every parentclass
                if len(leafdom)==0:
                    return f'{formhtml}<br/><p>Domain data for Function not found</p>'
                else:
                    field_list = list(set(map(lambda x: tuple([x.field_name,\
                            x.field_type,x.field_hint,x.field_o_num]), leafdom)))
                    for field in sorted(field_list,key=lambda f:f[3]):
                        print(f'''DEBUG: Deriving input field
                            field: {field},value:{leaf[field[0]]}''')
                        # notice the order in the Domain table matters
                        formhtml = f'''{formhtml}
            {self.derive_input_field(field,leaf[field[0]],leafdom)}'''
            else:
                # we are editing a failure cause
                actions = self.get_action_list(cursor,[leaf])
                formhtml = ''
                leafdom = list(filter(lambda x:x.parentclass==leaf.__nodename__(),\
                                     domain))
                # here we manipulate domain to make distinction between Failure Mode
                # and Failure Cause
                parents = list(filter(lambda x:x.id == leaf.parentid,tree))
                if len(parents) != 1:
                    print(f'ERROR: Could not locate parent of leaf {leaf.id}')
                else:
                    if parents[0].__class__.__name__ == FMEA_Failure_Mode.__name__:
                        formhtml = '<p>Failure Cause</p>'
                        for ld in leafdom:
                            if ld.field_hint is not None:
                                if ld.field_hint.find('ode')>=0:
                                    ld.field_hint = ld.field_hint.replace('Mode','Cause')
                            if ld.title is not None:
                                if ld.title.find('ode')>=0:
                                    ld.title = ld.title.replace('Mode','Cause')
                    else:
                        formhtml = '<p>Failure Mode</p>'
                        for ld in leafdom:
                            if ld.field_hint is not None:
                                if ld.field_hint.find('ause')>=0:
                                    ld.field_hint = ld.field_hint.replace('Cause','Mode')
                            if ld.title is not None:
                                if ld.title.find('ause')>=0:
                                    ld.title = ld.title.replace('Cause','Mode')
                filtered_tree = []
                if len(tree) > 0:
                    filtered_leaf = list(filter(lambda x:x.id == leaf.id,tree))
                    if len(filtered_leaf)>0:
                        filtered_tree = list(filter(lambda x:x.parentid is not \
                    None and filtered_leaf[0].__treecmppath__(tree,x)!=0,tree))
                field_list = []
                # TODO: Ensure that this triplet is unique for every parentclass
                if len(leafdom)==0:
                    return f'{formhtml}<br/><p>Domain data for Fail was not defined</p>'
                else:
                    field_list = list(set(map(lambda x: tuple([x.field_name,\
                            x.field_type,x.field_hint,x.field_o_num]), leafdom)))
                    for field in sorted(field_list,key=lambda f:f[3]):
                        # notice the order in the Domain table matters
                        formhtml = f'''{formhtml}
            {self.derive_input_field(field,leaf[field[0]],leafdom,filtered_tree)}'''
                    add_actions = ''
                    for ac in actions:
                        if leaf.id not in list(map(lambda x:int(x.strip()) if \
                         x.strip().isnumeric() else -1,ac.parentlist.split(','))):
                             add_actions = f'''{add_actions}
    <option value="({ac.id}){ac.title}">({ac.id}){ac.title}</option>'''
                    if len(add_actions)>0:
                        add_actions = f'''&nbsp;<span class="action-right">
    <a href="#" onclick="leafAddAction({leaf.id});return false">Add</a>
    <select id="add-action-to-leaf">{add_actions}</select>&nbsp;</span>'''
                    formhtml = f'''{formhtml}
            <a href="#" onclick="actionNew({leaf.id});return false">Add Action</a>
            {add_actions}
            <div id="action-list" class="action-list">
            {self.derive_action_list(actions,domain,tree=[leaf])}
            </div>'''
        formhtml = f'''<form method="POST" id="dlg-leaf-form" action="./apinojs?action=leafedit">
        <div id="dlg-leaf-form-content" class="dlg-form-content">{formhtml}</div></form>'''
        return formhtml
    def derive_node_list(self,actionid,treelist = []):
        # make list of nodes to delete from an action
        result_list = ''
        for le in treelist:
            result_list = f'''{result_list}
            <div id="act-nl-{le.id}" class="action-node">
             <a href="#fmeald-fmeaf-{le.id}" onclick="navigateAndHighlight('fmeald-fmeafm-{le.id}');return false">({le.id}){le.title}</a>&nbsp;
             <span class="nodes-right">
              <a href="#" onclick="actionDelete({actionid},{le.id});return false">&#9746;</a>
             </span>
            </div>'''
        return result_list
    def derive_action_edit(self,cursor,act,id=None,leafid=None,debug=True):
        # generate the HTML form to edit action details
        formhtml='<p>Action</p>'
        if debug: print(f'''Generating action edit form using act {str(act)}
        id "{id}" and leafid "{leafid}"''')
        domain = self.get_domain_list(cursor,FMEA_Action().__nodename__())
        field_list = list(set(map(lambda x: tuple([x.field_name,x.field_type,\
                                            x.field_hint,x.field_o_num]), domain)))
        # TODO: Ensure that this triplet is unique for every parentclass
        if len(domain)==0:
            formhtml = f'{formhtml}<br/><p>Domain data for Action was not defined</p>'
        else:
            for field in sorted(field_list,key=lambda f:f[3]):
            # notice the order in the Domain table matters
                formhtml = f'''{formhtml}
            {self.derive_input_field(field,act[field[0]],domain)}'''
        # TODO: Add 'Add failure mode' button and the list of failure modes
        if leafid is None:
            actnew = FMEA_Action().__nodeinband__({'id':id})
            res = actnew.__sqliteself__(cursor)
            if res is not None:
                leafid = actnew.parentlist.split(',')[0].strip()
        if leafid is None:
            pars = act.parentlist.split(',')
            if len(pars)>0:
                if pars[0].strip().isnumeric():
                    leafid = pars[0].strip()
        nodes_list = []
        detected_sheetid = None
        presumed_node = FMEA_Failure_Mode().__nodeinband__({'id':int(leafid)})
        res = presumed_node.__sqliteself__(cursor)
        if res is None:
            #maybe it's a sheetid
            presumed_sheet = FMEA_Function().__nodeinband__({'id':int(leafid)})
            res = presumed_sheet.__sqliteself__(cursor)
            if res is None:
                # let's give up and display the parentlist
                for p in act.parentlist.split(','):
                    if p.strip().isnumeric():
                        presumed_parent = FMEA_Failure_Mode().__nodeinband__\
                        ({'id':int(p.strip())})
                        presumed_parent.__sqliteself__(cursor)
                        nodes_list.append(presumed_parent)
            else:
                # so parentlist filtered by sheet id
                detected_sheetid = leafid
                for p in act.parentlist.split(','):
                    if p.strip().isnumeric():
                        presumed_parent = FMEA_Failure_Mode().__nodeinband__\
                        ({'id':int(p.strip())})
                        presumed_parent.__sqliteself__(cursor)
                        if presumed_parent.sheetid == leafid:
                            nodes_list.append(presumed_parent)
        else:
            # this is a tough one, should we use the node itself or those in the same sheet
            detected_sheetid = presumed_node.sheetid
            for p in act.parentlist.split(','):
                if p.strip().isnumeric():
                    presumed_parent = FMEA_Failure_Mode().__nodeinband__\
                     ({'id':int(p.strip())})
                    presumed_parent.__sqliteself__(cursor)
                    if presumed_parent.sheetid == presumed_node.sheetid:
                        nodes_list.append(presumed_parent)
        tree = []
        if detected_sheetid is not None:
            tree = self.get_sheet_tree(cursor,detected_sheetid)
            nodes_filter = list(l.id for l in nodes_list)
            tree = list(filter(lambda x:x.id not in nodes_filter and\
             x.__class__.__name__ == FMEA_Failure_Mode.__name__,tree))
        add_existing_node = f'''<a href="#" onclick="actionAddLeaf({act.id});return false">Add</a><select id="add-leaf-to-action" name="mangle-add-leaf-to-action">'''
        for le in tree:
            add_existing_node = f'''{add_existing_node}
            <option value="({le.id}):{le.title}">({le.id}):{le.title}</option>'''
        add_existing_node = f'''{add_existing_node}
        </select>'''
        if len(nodes_list)>0:
            add_existing_node = f'''{add_existing_node}
            <div class="node-list" id="action-node-list">
            {self.derive_node_list(act.id,nodes_list)}</div>'''
        return f'''<form method="POST" id="dlg-act-form" action="./apinojs?action=actionedit"
        class="dlg-form"><div id="dlg-act-form-content" class="dlg-form-content">
        {formhtml}</div></form>{add_existing_node}'''
    def derive_form_action(self,form_id,form_type="confirm"):
        # generate toolbar links to use on sidebar or main toolbar
        pass
    def compile_css(self,options=[]):
        css_script = '''
    :root { /* by default light scheme */
     --toolbar: 3vh;
     --font-a: 2vmin;
     --font-b: 3vmin;
     --font-c: 4vmin;
     --font-d: 5vmin;
     --color-lightest: #d5f4e6;
     --color-lighter:  #fefbd8;
     --color-light:    #c5d5c5;
     --color-dark:     #80ced6;
     --color-darker:   #e3e0cc;
     --color-darkest:  #618685;
     --color-a: var(--color-lightest);
     --color-b: var(--color-lighter);
     --color-c: var(--color-light);
     --color-d: var(--color-dark);
     --color-e: var(--color-darker);
     --color-f: var(--color-darkest);
    }
    media screen and (prefers-color-scheme: dark){
     :root{
     --toolbar: 3vh;
     --color-f: var(--color-lightest);
     --color-e: var(--color-lighter);
     --color-d: var(--color-light);
     --color-c: var(--color-dark);
     --color-b: var(--color-darker);
     --color-a: var(--color-darkest);
     }
    }
    media screen and (prefers-color-scheme: light){
     :root{
     --toolbar: 3vh;
     --color-a: var(--color-lightest);
     --color-b: var(--color-lighter);
     --color-c: var(--color-light);
     --color-d: var(--color-dark);
     --color-e: var(--color-darker);
     --color-f: var(--color-darkest);
     }
    }
    * {
     margin: 0;
     padding: 0;
     border: 0;
     font-size: var(--font-a);
     font-family: sans-serif;
    }
    body {
     display: flex;
     flex-flow: column nowrap;
     justify-content: center;
     align-items: flex-start;
     max-height: 100vh;
     overflow: hidden;
     height: 100vh;
     background: var(--color-a);
     background: linear-gradient(60deg, var(--color-a) 0%,var(--color-b) 39%, var(--color-c) 100%);
    }
    header, footer {
     display:flex;
     flex-flow:row nowrap;
     justify-content: space-between;
     align-items: stretch;
     width: 99.9vw;
     height: var(--toolbar);
     background: var(--color-f);
     color: var(--color-b);
     padding: 3px;
     border-left: 2px;
    }
    header a, footer a{
     text-decoration: none;
     color: var(--color-b);
    }
    .hdr-left {
     display:flex;
     order: 1;
     width: calc(33vw - 3px);/*  */
     text-align: left;
    }
    .hdr-cntr {
     order: 2;
     width: 33vw;/*  */
     text-align: center;
    }
    .hdr-right {
     /*display: flex; /* */
     display: float;
     float: right;/* */
     order: 3;
     flex-basis: auto;
     width: calc(33vw - 3px);/*  */
     text-align: right;
    }
    .content {
     height: calc(100vh - 4px - var(--toolbar) - var(--toolbar) ) ;
     width: 99vw;
     display: flex;
     flex: 1 1 auto;
    }
    .btn-link {
     border: none;
     outline: none;
     background: none;
     cursor: pointer;
     color: #0000EE;
     padding: 0;
     text-decoration: inherit;
     font-family: inherit;
     font-size: inherit;
    }
     ''' # TODO: Allow branding/themeing
        if 'table' in options:
            css_script += '''
    table {
     border-collapse: collapse;
     margin: 25px 0;
     font-size: var(--font-a);
     width: 100vw;
     box-shadow: 0 0 20px rgba(0, 0, 0, 0.15);
    }
    thead tr {
     background-color: var(--color-f);
     color: var(--color-c);
     text-align: left;
    }
    th, td {
     padding: 2vmin 2vmax;
    }
    tbody tr {
     border-bottom: 1px solid rgba(0, 0, 0, 0.15);
    }
    tbody tr:nth-of-type(even) {
     background-color: var(--color-c);
    }
    tbody tr:last-of-type {
     border-bottom: 1px solid var(--color-f);
    }
    .report-preview {
     max-width: 33vw;
     max-height: calc(100vh - 4px - var(--toolbar) - var(--toolbar) - var(--toolbar) );
     overflow-x: scroll;
     overflow-y: scroll;
    }'''
        if 'tree' in options:
            css_script += '''
    .editor {
     height: calc(100vh - 4px - var(--toolbar) - var(--toolbar) ) ;
     width: 300vmax;
     display: flex;
     /*flex: 1 1 auto;/* */
     justify-content: flex-start;
     overflow: scroll;
     overflow-x: scroll;
     overflow-y: scroll;
    }
    .tree {
     height: calc(200vmax - 6px - var(--toolbar) - var(--toolbar) ) ;
     width: calc(300vmax - 6px);/**/
     display: flex;
     justify-content: flex-start;/**/
     position: relative;/*  */
     flex-flow: column nowrap;
     align-content: flex-end;/**/
     /*top: 50%;*/
     /*transform: translate(0,50%);*/
     /*overflow: scroll;*/
     padding: 4px;
    }
    .tree ul {
     padding-left: 20px; position: relative;
     transition: all 0.5s;
     -webkit-transition: all 0.5s;
     -moz-transition: all 0.5s;
     display: -webkit-box;
     display: -ms-flexbox;
     display: flex;
     -webkit-box-orient: vertical;
     -webkit-box-direction: normal;
     -ms-flex-direction: column;
     flex-direction: column;
     -webkit-box-pack: center;
     -ms-flex-pack: center;
     justify-content: flex-start;/**/
    }
    .tree li {
     text-align: center;
     list-style-type: none;
     position: relative;
     padding: 5px 0 5px 20px;
     display: -webkit-box;
     display: -ms-flexbox;
     display: flex;
     justify-content: flex-start;
     align-items: left;
     transition: all 0.5s;
     -webkit-transition: all 0.5s;
     -moz-transition: all 0.5s;
    }
    .tree li::before, .tree li::after{
     content: '';
     position: absolute; left: 0; bottom: 50%;
     border-left: 1px solid var(--color-d);
     width: 20px; height: 50%;
    }
    .tree li::after{
     bottom: auto; top: 50%;
     border-top: 1px solid var(--color-f);
    }
    .tree li:only-child::after, .tree li:only-child::before {
     display: none;
    }
    .tree li:only-child {
     padding-left: 0;
    }
    .tree li:first-child::before, .tree li:last-child::after{
     border: 0 none;
    }
    .tree li:last-child::before{
     border-bottom: 1px solid var(--color-f);
     /*border-radius: 0 0 5px 0;
     -webkit-border-radius: 0 0 5px 0;
     -moz-border-radius: 0 0 5px 0;
     /* */
    }
    .tree li:first-child::after{
     /*border-radius: 0 0 0 5px;
     -webkit-border-radius: 0 0 0 5px;
     -moz-border-radius: 0 0 0 5px;
     /* */
    }
    .tree ul ul::before{
     content: '';
     position: absolute; left: 0; top: 50%;
     border-top: 1px solid var(--color-f);
     width: 20px; height: 0;
     }
    .tree ul::after  {
     content: ' ';
     min-width: 10vw;
     }
/*    .tree:first-child .leaf:not(.fix-top) {
     top: calc(50%);
     transform: translate(0,-50%);
    }
    .fix-top::before {
     content: ''
     min-height: 50vh ;
     top: 50%
    }
    .fix-top {
     top: 50vh;
     margin: 0;
    } */
    .leaf {
     position: relative;
     top: calc(50%);
     transform: translate(0,-50%);
     top 50%;/**/
     min-width: 5vw;
     max-width: 7.5vw;
     padding: 1px;
     /*margin: 2px;*/
     box-sizing: border-box;
     background: var(--color-c);
     display: flex;
     flex-flow: row nowrap;
     flex-sizing: fit-content;
     align-items: center;
     max-width: 40vw;
     max-height: 18vh;
     border: 1px solid var(--color-f);
     border-radius: 1vmin;
    }
    .leaf-highlight {
     position: relative;
     top: calc(50%);
     transform: translate(0,-50%);
     top 50%;/**/
     min-width: 5vw;
     padding: 1px;
     /*margin: 2px;*/
     box-sizing: border-box;
     background: var(--color-f);
     display: flex;
     flex-flow: row nowrap;
     flex-sizing: fit-content;
     align-items: center;
     max-width: 40vw;
     max-height: 18vh;
     border: 1px solid var(--color-c);
     border-radius: 1vmin;
    }
    .leaf-hidden {
     display: none;
    }
    .leaf a {
     text-decoration: none;
     color: var(--color-f);
     border-radius: 0.3em;
    }
    .leaf-highlight a {
     text-decoration: none;
     color: var(--color-c);
    }
    .leaf-ls, .leaf-rs, .leaf-title {
     order: 1;
     display: flex;
     flex-flow: column nowrap;
     align-items: stretch;
    }
    .leaf-title {
     padding-left: 0.5vw;
     padding-right: 0.5vw;
     max-width: 99%;
     display:flex;
     order:1;
     box-sizing: content-box;
     overflow-x: auto;
     text-align: left;
    }
    .leaf-tidiv {
     text-align: center;
    }
    .leaf-ls, .leaf-ls a{
     text-align: left;
    }
    .leaf-rs, .leaf-rs a{
     text-align: right;
    }
    .right-dlg {
     display: flex;
     flex-flow: column nowrap;
     background: var(--color-f);
     /*position:fixed;*/
     z-index: 1;
     top: calc(2vh + var(--toolbar));
     min-width: 33vw;
     height: calc( 92vh - var(--toolbar) - var(--toolbar) );
     left: 64vw;
     padding-top: 0;
     padding-left: 1vw;
     padding-right: 1vw;
     padding-bottom: 1vw;
     border: 1px solid var(--color-b);
     border-radius: 1vw;
     x-overflow: auto;
    }
    .right-dlg-wjs {
     display: flex;
     flex-flow: column nowrap;
     background: var(--color-f);
     /*position:fixed;*/
     z-index: 1;
     top: calc(2vh + var(--toolbar));
     min-width: 33vw;
     height: calc( 92vh - var(--toolbar) - var(--toolbar) );
     left: 64vw;
     padding-top: 0;
     padding-left: 1vw;
     padding-right: 1vw;
     padding-bottom: 1vw;
     border: 1px solid var(--color-b);
     border-radius: 1vw;
     overflow: hidden;
    }
    .righd-dlg-hdr:before {
     content: ''
    }
    .right-dlg-hdr {
     display: flex;
     flex-flow: row nowrap;
     justify-content: flex-end;
     position:sticky;
     top:0;
     right:0;
     background:var(--color-f);
    }
    .right-dlg-ftr {
     display: flex;
     flex-flow: row nowrap;
     justify-content: flex-end;
     position:fixed;
     bottom:0;
     right:0;
     background:var(--color-f);
    }
    .right-dlh-hdr-a{
     display: flex;
     text-align: right;
     position: relative;
     align-items: right;
     text-decoration: none;
     color: var(--color-b);
    }
    .right-dlg-hdr a{
     display: flex;
     text-align: right;
     position: relative;
     align-items: right;
     text-decoration: none;
     color: var(--color-b);
    }
    .right-dlg-content {
     color: var(--color-b);
    }
    .right-dlg-hidden, .act-legend-h {
     display: none;
    }
    .act-legend {
     display: flex;
    }
    .action-list, .node-list {
     padding-top: 1vh;
    }
    .action-node, .action {
     text-align: left;
     padding-left: 1em;
     padding-right: 1em;
     border: 1px solid var(--color-c);
     border-radius: 0.5em;
     background: var(--color-e);
    }
    .action-right, .nodes-right {
     float:right;
    }
    .dlg-form-content {
    }
    .btn-link {
    }
    .edit-d {
     margins: 1px;
     width: 100%;
    }
    .edit-lbl {
     display: inline-block;
     width: 30%;
    }
    .edit-in {
     display: inline-block;
     width: 67%;
     border: 1px solid var(--color-b)
    }
    .edit-in::not(type(text))::before {
     content: '&nbsp;';
    }
    .edit-in-hidden {
     display: none;
    }
    .edit-in-widetext {
     display: inline-block;
     width: 100%;
    }'''
    # TODO: Add css for action list and forms
        return css_script
    def compile_js(self,options=[]):
        js_script = '''
/*General purpose functions*/
function applyClass(id,cl,or_else='#') {
  target = document.getElementById(id);
  if(target) {
    target.classList.remove(...target.classList);
    target.classList.add(cl);
    return false; /* Do not follow link on anchor */
    } else return or_else; /*Follow link if element not found*/
}
function toggleBetweenClasses(tid,cla,clb,or_else='#'){
  target = document.getElementById(tid);
  if (target){
   if (target.classList.contains(clb)){
    target.classList.replace(clb,cla);
    return false;}
   else {
    target.classList.replace(cla,clb);
    return false;}
  } else return or_else;
}
function sleep (time) {
  return new Promise((resolve) => setTimeout(resolve, time));
}
function extract_id() {
    return window.location.pathname.match(/\d+/)[0];
}
function ajaxHelperDestination(url,formElementById,destElementById) {
/* wrap the callback to spill the response */
  let xhr = new XMLHttpRequest();
  target = document.getElementById(destElementById);
  let callspill = function(tid) {target = document.getElementById(tid);if(target){target.innerHTML = xhr.response+'<!-- updated -->';}}
  xhr.open('PUT',url);
  xhr.onload = () => callspill(destElementById);
  if (formElementById === null || formElementById == 'null_form')
   {console.log('DEBUG: Ajax found no form');xhr.send();}
   else { let formElem = document.getElementById(formElementById);
    if (formElem) { console.log('DEBUG: found form',formElem);
     let formData = new FormData(formElem);
     if (formData) { console.log('DEBUG: found form data',formData);
      xhr.send(formData);} else {console.log('DEBUG: Could not extract form data!');}
     } else {console.log('DEBUG: Could not find form ',formElementById);}
    }
  return xhr;
}
/* Global function */
function FMEA_Init(){
/* These are not the droids you are looking for */
  applyClass("right-dlg","right-dlg-wjs"); /* disable manual scrolling of action list */
  let allAnchors = document.getElementsByTagName('a');
  let allEventFuncs = []
  for (i=0;i<allAnchors.length;i++){
  if (allAnchors[i].onclick){
    allAnchors[i].addEventListener("click",allAnchors[i].onclick);
    allAnchors[i].href="#";
   }
  }
  return true;
}
function FMEA_New_Sheet(){
  let xhr = new XMLHttpRequest();
  xhr.open('PUT','/fmea/jsapi/0/sheetnew')
  xhr.onload = () => function(xhr){window.location = xhr.response;}
  xhr.send();
}
function FMEA_Delete_Sheet(id){
  target = document.getElementById("a-sheet-del-"+id);
  target.setAttribute("onclick","window.location = '/fmea/redirect/"+id+"/delsheet'");
  target.innerHTML="Yes, I am sure! ";
  cancel = document.createElement("a");
  cancel.setAttribute("id","a-sheet-del-cancel-"+id);
  cancel.setAttribute("href","#");
  cancel.setAttribute("onclick","d=document.getElementById('a-sheet-del-"+id+
  "');d.innerHTML='Delete';d.setAttribute('onclick','FMEA_Delete_Sheet("+id+
  ");return false');d.parentNode.removeChild(d.nextSibling);return false");
  cancel.innerHTML=" No, cancel that!";
  if (target.nextSibling === null){
   target.parentNode.insertBefore(cancel,target.nextSibling);
 }
}
function FMEA_sheetOpen(){
 target = document.getElementById('open-form-in');
 if (target){
  if (target.dataset.disabled){
   console.log('NOTICE: Multiple clicks detected on "open-form-in"!');
  } else {
   target.setAttribute('data-disabled',true);
   target.click();
   sleep(100).then(()=>{
    document.getElementById('open-form-in').removeAttribute('data-disabled');
   });
  }
 } else {console.log('ERROR: "open-form-in" was not found!');}
 return false;
}
function reportView(sheet_id,report_name,report_type){
  target_id = report_name+'-prev';
  target_url = '/fmea/redirect/'+sheet_id+'/report?name='+report_name+'&type='+report_type;
  if (report_name == 'aadc'){
   option_target = document.getElementById('aadc-opts');
   target_url+='&opts='+option_target.value
  }
  if (report_type == 'preview'){
   ajaxHelperDestination(target_url,'null_form',target_id);
  } else {
   window.location.href = target_url;
  }
  return false;
}
'''
        if 'editor' in options:
            js_script += '''
function scrollSync(){
  /* ensure that action list and main editor are synched scrolling */
   target = document.getElementById("right-dlg");
   source = document.getElementById("editor");
   if (target === null || source === null) {
    return false; } else {
    /* FIX: Disable proportional scrolling as it does not feel intuitive
    position_pct = source.scrollTop/(source.scrollHeight - source.offsetHeight);
    target_scroll = (target.scrollHeight - target.offsetHeight)*position_pct;
    target.scrollTo(0,target_scroll);
    */
    target.scrollTo(0,source.scrollTop);
    return true;}
}
function treeCollapse(id,position) {
  /* either select and hide tree in place or request adjusted tree via jsapi */
  sheet_id = extract_id(); /* WARNING: Assumes /edit/{sheetid}/api links */
  api_endpoint = '/fmea/jsapi/'+sheet_id+'/tree';
  api_proposed_call = '?act=hi'+position[0]+'&id='+id;
  current_call = window.location.search;
  if (current_call.includes(api_proposed_call)) {
   api_full_call = current_call.replace(api_proposed_call,'').replace('&&','&').replace('?&','?');
  } else { api_full_call = current_call+api_proposed_call; }
  ajaxHelperDestination(api_endpoint+api_full_call,'null_form','tree');
  return false;
}
function treeActions(ignorea, ignoreb){
  /* retrieve the action list for current sheet */
  sheet_id = extract_id();
  api_endpoint = '/fmea/jsapi/'+sheet_id+'/actions';
  target_self    = document.getElementById('hdr-actions');
  target_header  = document.getElementById('right-dlg-hdr');
  if (target_self.attributes['onclick'].textContent.includes('treeActions')) {
   target_self.attributes['onclick'].textContent = target_self.attributes[ 'onclick' ].textContent.replace('treeActions','applyClass');
   target_header.innerHTML = '<a class="right-dlg-hdr-a" href="#" onclick="applyClass('+"'right-dlg','right-dlg-hidden')"+';return false">Hide</a>&nbsp;';
  ajaxHelperDestination(api_endpoint,'null_form','right-dlg-content');
  applyClass('right-dlg','right-dlg-wjs');
  } else { target_self.attributes['onclick'].textContent = target_self.attributes[ 'onclick' ].textContent.replace('applyClass','treeActions');
  applyClass('right-dlg','right-dlg-wjs');
  }
  return false;
  }
function leafPrepareDelete(id) {
  /* build the dialog in place (using hidden form) to confirm delete */
  sheet_id = extract_id(); /* WARNING: Assumes /edit/{sheetid}/api links */
  api_endpoint = '/fmea/jsapi/'+sheet_id+'/leafdel';
  target_content = document.getElementById('right-dlg-content');
  target_header  = document.getElementById('right-dlg-hdr');
  target_toggle  = document.getElementById('hdr-right');
  delete_form = '<form id="dlg-leafdel-form" class="dlg-form"';
  delete_form+= 'method="PUT" action="'+api_endpoint+'">';
  delete_form+= '<input type="hidden" name="id" value="'+id+'"/>';
  delete_form+= '<p> Are you sure you want to delete node '+id;
  delete_form+= ' and all its children?</p></form>';
  delete_head = '<input type="submit" form="dlg-leafdel-form" value="Yes"';
  delete_head+= 'class="link-btn" onclick="leafPerformDelete('+"'dlg-leafdel-form')";
  delete_head+= ';return false"/>&nbsp;';
  if (target_toggle.innerHTML.includes('treeActions')) {
  delete_head+= '<a href="#" onclick="applyClass('+"'right-dlg','right-dlg-hidden')";
  delete_head+= ';return false">';
  } else {
  delete_head+= '<a href="#" onclick="treeActions('+"'right-dlg','right-dlg-hidden')";
  delete_head+= ';return false">';
  }
  delete_head+= 'Cancel</a>';
  target_content.innerHTML = delete_form;
  target_header.innerHTML  = delete_head;
  applyClass('right-dlg','right-dlg-wjs');
  return false;
}
function leafPrepareEdit(parent,id) {
  /* retrieve the edit form via ajax */
  sheet_id = extract_id(); /* WARNING: Assumes /edit/{sheetid}/api links */
  ajax_endpoint_edit = '/fmea/jsapi/'+id+'/leafedit';
  ajax_endpoint_new  = '/fmea/jsapi/'+parent+'/leafnew';
  api_endpoint  = '/fmea/jsapi/'+sheet_id+'/leafupdate';
  if (id==null) {
   xhr = ajaxHelperDestination(ajax_endpoint_new,null,'right-dlg-content');
  } else {
   xhr = ajaxHelperDestination(ajax_endpoint_edit,null,'right-dlg-content');
  }
  target_header  = document.getElementById('right-dlg-hdr');
  target_toggle  = document.getElementById('hdr-right');
  edit_head = '<a href="#" onclick="leafPerformEdit('+"'dlg-leaf-form')";
  edit_head+= ';return false">Apply</a>&nbsp;';
  if (target_toggle.innerHTML.includes('treeActions')) {
  edit_head+= '<a href="#" onclick="applyClass('+"'right-dlg','right-dlg-hidden')";
  edit_head+= ';return false">';
  } else {
  edit_head+= '<a href="#" onclick="treeActions('+"'right-dlg','right-dlg-hidden')";
  edit_head+= ';return false">';
  }
  edit_head+= 'Cancel</a>';
  target_header.innerHTML = edit_head;
  applyClass('right-dlg','right-dlg-wjs');
  return xhr;
}
function leafPrepareMove(id) {
  /* retrieve the edit form via ajax, replace parentid with selector and
     make all the others read only
   */
  xhr = leafPrepareEdit(null,id);
  sleep(500).then(() => {
  to_reactivate = document.getElementById('edit-in-parentid');
  to_block = document.querySelectorAll('.edit-d:not(#edit-in-id,#edit-in-parentid)');
  for (i=0;i<to_block.length;i++){to_block[i].setAttribute('readonly','readonly');}
  to_reactivate.removeAttribute('disabled');
  to_reactivate.removeAttribute('readonly');
  document.querySelectorAll('#dlg-leaf-form-content p')[0].innerText = 'Select the new parent ID to move this node to';
  });
  return false;
}
function leafPerformDelete(formid){
  /* send formdata via ajax, the result replaces the tree */
  sheet_id = extract_id();
  ajax_endpoint = '/fmea/jsapi/'+sheet_id+'/leafdel';
  ajaxHelperDestination(ajax_endpoint,formid,'tree');
  target_toggle  = document.getElementById('hdr-right');
  if (target_toggle.innerHTML.includes('treeActions')) {
   applyClass('right-dlg','right-dlg-hidden');
  } else {
   treeActions('right-dlg','right-dlg-hidden');
  }
  return false;
}
function leafPerformEdit(formid){
  /* send formdata via ajax, the result replaces the tree */
  sheet_id = extract_id();
  ajax_endpoint = '/fmea/jsapi/'+sheet_id+'/leafupdate';
  /* HACK: Remove disabled from parentid
  target_parentid = document.getElementById('edit-in-parentid')
  target_parentid.removeAttribute('disabled');
  target_parentid.setAttribute('readonly','readonly'); */
  ajaxHelperDestination(ajax_endpoint,formid,'tree');
  target_toggle  = document.getElementById('hdr-right');
  if (target_toggle.innerHTML.includes('treeActions')) {
   applyClass('right-dlg','right-dlg-hidden');
  } else {
   treeActions('right-dlg','right-dlg-hidden');
  }
  return false;
}
function leafAddAction(id){
    ajax_endpoint = '/fmea/jsapi/'+id+'/leafactadd?addact=';
    source_action = document.getElementById('add-action-to-leaf');
    source_value = source_action.value;
    extracted_action_id = source_value.match(/^.*?\([^\d]*(\d+)[^\d]*\).*$/)[1];
    if (extracted_action_id != null){
     ajaxHelperDestination(ajax_endpoint+extracted_action_id,null,'right-dlg-content');
    }
    else {
     console.log('DEBUG: Cannot work with '+ajax_endpoint+extracted_action_id);
    }
    return false;
}
function actionEdit(actionid,backToElement){
  /* retrieve the edit form via ajax, update the backToElement with the action list */
  sheet_id = extract_id();
  ajax_endpoint       = '/fmea/jsapi/'+actionid+'/actionedit?leafid='+sheet_id;
  api_endpoint_large  = '/fmea/jsapi/'+sheet_id+'/actionup';
  target_content = document.getElementById('right-dlg-content');
  target_header  = document.getElementById('right-dlg-hdr');
  if (backToElement != '*') {
  /* */
   /*leafPerformEdit('dlg-leaf-form');*/
   applyClass('right-dlg','right-dlg-wjs'); /* Ensure that dialog stays open */
   target_in_leaf = document.getElementById('edit-in-id');
   backup_content = target_content.innerHTML;
   leaf_id = target_in_leaf.value;
   api_endpoint_leaf   = '/fmea/jsapi/'+leaf_id+'/leafactup?leafid='+sheet_id;
   actedit_head = '<a href="#" onclick="actionUpdate('+"'dlg-act-form'";
   actedit_head+= ','+leaf_id+');return false">Apply</a>&nbsp;<a href="#"';
   actedit_head+= ' onclick="leafPrepareEdit(null,'+leaf_id+');return false">';
   actedit_head+= 'Cancel</a>';
   target_header.innerHTML = actedit_head;
   ajaxHelperDestination(ajax_endpoint,null,'right-dlg-content');
   sleep(500).then(()=>{
    /* implement here saving the current node and return hints*/
   })
  } else {
   actedit_head = '<a href="#" onclick="actionUpdate('+"'dlg-act-form','*'";
   actedit_head+= ');return false">Apply</a>&nbsp;<a href="#"';
   actedit_head+= ' onclick="treeActions('+"'right-dlg','x'"+');return false">';
   actedit_head+= 'Cancel</a>';
   target_header.innerHTML = actedit_head;
   ajaxHelperDestination(ajax_endpoint,null,'right-dlg-content');
  }
  applyClass('right-dlg','right-dlg-wjs');
  return false;
}
function actionNew(leafid,backToElement){
  /* retrieve edit form via ajax, append leaf to parentlist, update the backToElement */
  ajax_endpoint   = '/fmea/jsapi/'+leafid+'/actionnew';
  api_endpoint    = '/fmea/jsapi/'+leafid+'/leafactup';
  target_content = document.getElementById('right-dlg-content');
  target_header = document.getElementById('right-dlg-hdr');
  /* ignore for now the backToElement parameter */
  /*leafPerformEdit('dlg-leaf-form');*/
  applyClass('right-dlg','right-dlg-wjs'); /* Ensure that dialog stays open */
  sleep(500).then(()=>{
    backup_content = target_content.innerHTML;
    actedit_head = '<a href="#" onclick="actionUpdate('+"'dlg-act-form'";
    actedit_head+= ','+leafid+');return false">Apply</a>&nbsp;<a href="#"';
    actedit_head+= ' onclick="leafPrepareEdit(null,'+leafid+');return false">';
    actedit_head+= 'Cancel</a>';
    target_header.innerHTML = actedit_head;
    ajaxHelperDestination(ajax_endpoint,'dlg-leaf-form','right-dlg-content')
    sleep(500).then(()=>{
    /* implement here saving the current node and return hints*/
    });
   });
  return false;
}
function actionDelete(actionid,leafid,backToElement) {
  /* retrieve action list after removing actionid from leafid
     no confirmation
   */
  if (leafid == '*'){
   form_id = extract_id();
   api_endpoint_list = '/fmea/jsapi/'+form_id+'/actiondel?delact='+actionid;
   target_content = document.getElementById('right-dlg-content');
   /* TODO: See if confirmation would be useful */
   ajaxHelperDestination (api_endpoint_list,null,'right-dlg-content');
  } else {
   api_endpoint_leaf = '/fmea/jsapi/'+leafid+'/leafactdel?delact='+actionid;
   target_content = document.getElementById('right-dlg-content');
   ajaxHelperDestination (api_endpoint_leaf,null,'right-dlg-content');
  }
  return false;
}
function actionUpdate(formid,backToElement){
   /* perform the actual action callback */
   console.log('DEBUG: Sending form data from '+formid+' going to element '+backToElement);
   if (backToElement == '*'){
    sheet_id = extract_id();
    ajax_endpoint_large = '/fmea/jsapi/'+sheet_id+'/actionup';
    ajaxHelperDestination(ajax_endpoint_large,formid,'right-dlg-content');
    target_header  = document.getElementById('right-dlg-hdr');
    target_header.innerHTML = '<a class="right-dlg-hdr-a" href="#" onclick="applyClass('+"'right-dlg','right-dlg-hidden')"+';return false">Hide</a>&nbsp;';
   } else {
    console.log('DEBUG: Reached leaf redirect')
    ajax_endpoint_leaf  = '/fmea/jsapi/'+backToElement+'/leafactup';
    ajaxHelperDestination(ajax_endpoint_leaf,formid,'right-dlg-content');
    target_header  = document.getElementById('right-dlg-hdr');
    edit_head = '<a href="#" onclick="leafPerformEdit('+"'dlg-leaf-form')";
    edit_head+= ';return false">Apply</a>&nbsp;';
    if (target_toggle.innerHTML.includes('treeActions')) {
     edit_head+= '<a href="#" onclick="applyClass(';
     edit_head+= "'right-dlg','right-dlg-hidden')"+';return false">';
    } else {
     edit_head+= '<a href="#" onclick="treeActions(';
     edit_head+= "'right-dlg','right-dlg-hidden')"+';return false">';
    }
    edit_head+= 'Cancel</a>';
    target_header.innerHTML = edit_head;
   } /* TODO: Implement the big list return */
   sleep(500).then(()=>{
    ajax_endpoint = '/fmea/jsapi/'+extract_id()+'/tree';
    ajaxHelperDestination(ajax_endpoint,null,'tree');
   })
   return false;
}
function actionAddLeaf(id){
    ajax_endpoint = '/fmea/jsapi/'+id+'/actionaddnode?leafid=';
    source_leaf = document.getElementById('add-leaf-to-action');
    source_value = source_leaf.value;
    extracted_leaf_id = source_value.match(/^.*?\([^\d]*(\d+)[^\d]*\).*$/)[1];
    if (extracted_leaf_id != null){
     /* TODO: Add form id parameter later */
     ajaxHelperDestination(ajax_endpoint+extracted_leaf_id,'dlg-act-form','right-dlg-content');
    }
    else {
     console.log('DEBUG: Cannot work with '+ajax_endpoint+extracted_leaf_id);
    }
    return false;
}
function navigateAndHighlight(id){
    target = document.getElementById(id);
    target.scrollIntoView();
    applyClass(id,'leaf-highlight');
    sleep(500).then(()=>{applyClass(id,'leaf');});
}
'''
        return js_script
    def derive_node_as_a_for_open(self,node,text):
        print(f'DEBUG: Comparing "{str(node)}" with "{text}"')
        if node['title']==text or text=='title':
            return f'''<a href="/fmea/edit/{node.id}/apidefault">{text}</a>
            &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
            <a href="/fmea/redirect/{node.id}/downloadsheet">Save As</a>&nbsp;
            <a id="a-sheet-del-{node.id}" onclick="FMEA_Delete_Sheet({node.id});
            return false" href="#">Delete</a>'''
        else:
            return text
    def report_generate(self,id,name,type='preview',reop=['both'],debug=True):
        # generate reports from data in one sheet
        # id is the sheet id
        # name can be 'afc', 'fmbrl' or 'aadc'
        # type can be 'preview', 'csv','excel'
        cursor = self.get_db_connection()
        tree = self.get_sheet_tree(cursor,id)
        actions = self.get_action_list(cursor,tree)
        domain = self.get_domain_list(cursor)
        cursor.connection.close()
        fc_range = self.app.config['MAX_TREE_DEPTH']+1
        re_range = self.app.config['PREVIEW_LINES']
        ld_range = self.app.config['MAX_CHARS_DESCRIPTION']
        if name == 'afc':
            # actions by failure cause
            report_header = ['Function']
            for i in range(fc_range):
                if i == 0:
                    report_header.append(f'Failure mode')
                else:
                    report_header.append(f'Failure cause {i}')
            report_header.append('Long description')
            report_header.append('Means of identification')
            report_header.append('Risk')
            action_types = list(map(lambda x:f'Action category {x.field_option.lower()}',\
             filter(lambda y:y.table_name == FMEA_Action().__sqlitetable__() and \
             y.field_name == 'category',domain)))
            for at in action_types:
                report_header.append(at)
            report_header.append('Action category not clasified')
            if debug: print(f'DEBUG: generated header as {report_header}')
            tree_selection = []
            act_parents = []
            for act in actions:
                this_parents = list(set(act.parentlist.split(',')))
                act_parents.append({'id':act.id,'title':act.title,\
                 'category':act.category,'parents':this_parents})
                tree_selection.extend(this_parents)
            tree_selection = sorted(set(tree_selection))
            if debug: print(f'Tree selection {tree_selection}')
            if debug: print(f'Actions with parents {act_parents}')
            failure_cause_list = []
            tree = tree[0].__treesort__(tree)
            for le in tree:
                # we are forced to recalculate path here
                if le.parentid is None: continue
                text_path = []
                if le.parentid != id and le.parentid is not None:
                    if len(failure_cause_list)>0:
                        self_fcl = list(filter(lambda x:x['id']==le.parentid,\
                                                        failure_cause_list))
                        if len(self_fcl)>0:
                            text_path.extend(self_fcl[0]['text_path'])
                text_path.append(le.title)
                failure_cause_list.append({'id':le.id,'title':le.title,\
                 'text_path': text_path, 'means_of_identification':\
                 le.means_of_identification if le.__contains__('means_of_identification')\
                 else '', 'risk': le.risk_level if le.__contains__('risk_level') else '',\
                 'description': le.description if le.__contains__('decription') else ''})
            if debug: print(f'Failures are {failure_cause_list}')
            fc_with_act = list(reversed(list(filter(lambda x:str(x['id']) in tree_selection,\
                failure_cause_list))))
            report_depth = 1
            if debug: print(f'Failure causes with actions {fc_with_act}')
            if type == 'preview':
                report_depth = 0-re_range
            report_line = []
            while len(fc_with_act)>0 and report_depth != 0:
                report_depth +=1
                record = fc_with_act.pop()
                if debug: print(f'DEBUG: Popped record {record}')
                report_line.append({'id':record['id'],'line': record['text_path'].copy()})
                report_cr = len(report_line)-1
                if debug: print(f'DEBUG: Working on report line {report_cr}')
                for i in range(fc_range-len(report_line[report_cr]['line'])+1):
                    report_line[report_cr]['line'].append('')
                if debug: print(f'Appending means {record["means_of_identification"]} and risk {record["risk"]}')
                if type == 'preview' and len(record['description']) > ld_range:
                    report_line[report_cr]['line'].append(record['description'][:ld_range]+'...')
                else:
                    report_line[report_cr]['line'].append(record['description'])
                report_line[report_cr]['line'].append(record['means_of_identification'])
                report_line[report_cr]['line'].append(record['risk'])
                to_reintroduce = False
                if debug: print(f'DEBUG: We have {len(action_types)} categories as: {action_types}')
                for category in action_types:
                    acts = list(filter(lambda x:str(record['id']) in x['parents'] and \
                     f'Action category {x["category"].lower()}' == category,act_parents))
                    if debug: print(f'DEBUG: Filtered acts by {category} and {record["id"]} - {acts}')
                    if len(acts) == 0:
                        report_line[report_cr]['line'].append('')
                    else:
                        report_line[report_cr]['line'].append(acts[0]['title'])
                        act_parents[act_parents.index(acts[0])]['parents'].\
                            remove(str(record['id']))
                        if debug: print(f'DEBUG: New parents {acts[0]["parents"]}')
                        if len(acts)>1:
                            to_reintroduce = True
                acts = list(filter(lambda x:record['id'] in x['parents'] and \
                     f'Action category {x["category"]}' not in action_types,act_parents))
                if debug: print(f'DEBUG: Report line looks like {report_line[report_cr]["line"]}')
                if len(acts) == 0:
                    report_line[report_cr]['line'].append('')
                else:
                    report_line[report_cr]['line'].append(acts[0]['title'])
                    act_parents.remove(acts[0])
                    if len(acts)>1:
                        to_reintroduce = True
                if to_reintroduce:
                    fc_with_act.append(record)
            return {'header':report_header,'lines':report_line}
        if name == 'fmbrl':
            sheets = list(filter(lambda x:x.parentid is None,tree))
            failure_modes = list(filter(lambda x:x.__class__.__name__ == \
             FMEA_Failure_Mode.__name__,tree))
            report_header = ['Risk level','Discipline']
            for i in range(fc_range):
                if i == 0:
                    report_header.append(f'Failure mode')
                else:
                    report_header.append(f'Failure cause {i}')
            report_header.append('Description')
            tree[0].__treesort__(tree)
            report_line = []
            report_cr = 0
            for fm in failure_modes:
                report_line.append({'id':fm.id,'line':[fm['risk_level'],\
                    fm['discipline']]})
                if report_cr > 0:
                    for i in range(len(fm._path_)-3):
                        report_line[report_cr]['line'].append(\
                         report_line[report_cr-1]['line'][i+2])
                report_line[report_cr]['line'].append(fm.title)
                for i in range(fc_range-len(report_line[report_cr]['line'])+2):
                    report_line[report_cr]['line'].append('')
                if type == 'preview' and len(fm.description) > ld_range:
                    report_line[report_cr]['line'].append(fm.description[:ld_range]+'...')
                else:
                    report_line[report_cr]['line'].append(fm.description)
                report_cr+=1
                if type == 'preview' and report_cr > re_range:
                    break # that's enough
            return {'header':report_header,'lines':report_line}
        if name == 'aadc':
            # actions at different criticality
            # has two coordinates:
            # 1. for all sheet asset/failure risks
            # 2. for action template equipment if it's not null
            report_header = ['Equipment Type','Equipment','Equipment tag','Criticality',\
                'Failure risk','Action','Frequency','Description']
            current_eqptty = 'Equipment level'
            sheets = list(filter(lambda x:x.parentid is None,tree))
            current_eqpttn = sheets[0].asset_description
            current_eqpttg = sheets[0].asset_name
            current_eqpttc = sheets[0].asset_criticality
            current_fmeari = ''
            failure_modes = list(filter(lambda x:x.__class__.__name__ == \
             FMEA_Failure_Mode.__name__,tree))
            tree_selection = []
            act_parents = []
            for act in actions:
                this_parents = list(filter(lambda y:y is not None,list(set(map(\
                 lambda  x:int(x.strip()) if x.strip().isnumeric() else None,\
                 act.parentlist.split(','))))))
                tree_selection.extend(this_parents)
            tree_selection = sorted(set(tree_selection))
            failure_modes = list(filter(lambda x:x.id in tree_selection,failure_modes))
            report_line = []
            act_risk = []
            report_cr = 0
            waiting_actions = actions.copy()
            while len(waiting_actions) > 0 and (report_cr < re_range or type !=\
             'preview') and ('equipment level' in reop or 'both' in reop):
                if len(act_risk) == 0:
                    act = waiting_actions.pop()
                    apl = list(filter(lambda y:y is not None,list(map(lambda \
                     x:int(x.strip()) if x.strip().isnumeric() else None,\
                     act.parentlist.split(',')))))
                    act_risk = list(set(map(lambda x:x.risk_level,list(filter(\
                     lambda y:y.id in apl,failure_modes)))))
                if len(act_risk) == 0:
                    continue
                current_fmeari = act_risk.pop()
                report_line.append({'id':act.id,'line':[current_eqptty,current_eqpttn,\
                 current_eqpttg,current_eqpttc,current_fmeari,act.title]})
                if current_eqpttc.lower() in ['a','b','c','d']:
                    report_line[report_cr]['line'].append(\
                     act[f'frequency_for_{current_eqpttc.upper()}_criticality'])
                else:
                    report_line[report_cr]['line'].append('-')
                if type == 'preview' and len(act['description']) > ld_range:
                    report_line[report_cr]['line'].append(act['description'][:ld_range]+'...')
                else:
                    report_line[report_cr]['line'].append(act['description'])
                report_cr += 1
            if (report_cr < re_range or type != 'preview') and ('class level' in\
             reop or 'both' in reop):
                current_eqptty = 'Class level'
                for act in actions:
                    current_eqpttn = act.templating_equipment
                    current_eqpttg = act.templating_group
                    for current_eqpttc in ['a','b','c','d']:
                        report_line.append({'id':act.id,'line':[current_eqptty,\
                         current_eqpttn,current_eqpttg,current_eqpttc,1,act.title,\
                         act[f'frequency_for_{current_eqpttc.upper()}_criticality']]})
                        if type == 'preview' and len(act['description']) > ld_range:
                            # TODO: The max description len for preview -> setting
                            report_line[report_cr]['line'].append(act['description']\
                             [:ld_range]+'...')
                        else:
                            report_line[report_cr]['line'].append(act['description'])
                        report_cr += 1
                        if report_cr >= re_range and type == 'preview': break
                    if report_cr >= re_range and type == 'preview': break
            return {'header':report_header,'lines':report_line}
        return {'header': ['Not Implemented'],'lines':[{'id':0,'line':['-']}]}
    def derive_report(self,report):
        # represent html of a report (or report preview) having header and lines
        report_html = ''
        for h in report['header']:
            report_html = f'{report_html}<th>{h}&nbsp;</th>'
        report_html = f'<tr>{report_html}</tr>'
        for l in report['lines']:
            line_html = ''
            for f in l['line']:
                line_html = f'{line_html}<td>{f}&nbsp;</td>'
            if len(line_html)>0:
                report_html = f'{report_html}<tr>{line_html}</tr>'
        return f'<table>{report_html}</table>'
    def util_new_node(self,cursor):
        max_func_id = FMEA_Function().__sqlitenextid__(cursor)
        max_fmea_id = FMEA_Failure_Mode().__sqlitenextid__(cursor)
        return max(max_func_id if max_func_id is not None else 0,\
                   max_fmea_id if max_fmea_id is not None else 0)
    def util_clean_name(self,s):
        # turn any string record into an identifier
        try:
            return ''.join([ (c if (c.isidentifier() and i == 0) else\
             (f'_{c}' if (i == 0 and c.isalnum())  else ( '_' if i == 0 else\
             (c if c.isalnum() else '_')))) for i,c in enumerate(str(s))]) \
             if type(str(s)).__name__.lower().find('str') >= 0 else None
        except:
            return None
    def handle_add_action(self,cursor,tree,args,formdata,stage):
        # perform multi-step create/update of a record
        pass
    def handle_route(self,path='/',action='index',id=0,apitype='apinojs',debug=False):
        # handle the flask routes
        if debug: print(f'Called handle route with action:{action},id:{id},apitype={apitype}')
        if action == 'redirect' or action == 'proxy':
            cursor = self.get_db_connection()
            if apitype == 'newsheet' or apitype == 'sheetnew':
                new_id = self.util_new_node(cursor)
                cursor.connection.close()
                return self.redir(f'/fmea/edit/{new_id}/apidefault', code=302)
            if apitype == 'delsheet':
                tree = self.get_sheet_tree(cursor,id)
                actions = self.get_action_list(cursor,tree)
                root = list(filter(lambda x:x.parentid is None,tree))[0]
                root.delete_leaf(cursor,tree,actions)
                cursor.connection.close()
                return self.redir('/fmea',code=302)
            if apitype == 'uploadsheet':
                filename = ''
                try:
                    if (self.request.method in ['POST','PUT'] and \
                     'sheetfile' in self.request.files):
                        file = self.request.files['sheetfile']
                        if debug: print(f'DEBUG: Found {file}')
                        if (len(file.filename)>1 and (file.filename.find('.sqlite3')\
                         or file.filename.find('.fmea') or file.filename.find('.fmeasheet'))):
                            if not self.path.exists(self.app.config['template_folder']):
                                self.mkdir(self.app.config['template_folder'])
                            filename = self.path.join(self.app.config["template_folder"],\
                             f'{file.filename.split(".")[0]}_save.sqlite3')
                            while self.path.exists(filename):
                                # TODO: Find a cleaner way to ensure correct unique document
                                filename = filename.replace('.fmea','_.fmea')
                            file.save(filename)
                            newtree = self.import_from_file(filename,cursor,self.sqlite3)
                            if len(newtree) == 0:
                                raise Exception('sheetFileEmpty')
                                #return self.redir('/fmea?importError=sheetFileEmpty')
                            else:
                                destination_sheet = list(filter(lambda x:x.parentid\
                                 is None,newtree))[0].id
                                return self.redir(f'/fmea/edit/{destination_sheet}/apidefault',\
                                 code=302)
                        else:
                            raise Exception('improperFilename')
                    else:
                        raise Exception('invalidUseOfForm')
                except Exception as e:
                    return self.redir(\
                     f'/fmea?importError={e.__class__.__name__}&message={str(e.args[0])}',\
                     code=302)
                finally:
                    # TODO: Delete the files
                    cursor.connection.close()
                    try:
                        self.rmfile(filename)
                    except Exception as e:
                        print(f'ERROR: Unable to delete {filename} saying {e._class__.__name__}-{e.args}')
            if apitype == 'downloadsheet':
                # here id is the sheet_id we want to download
                tree = self.get_sheet_tree(cursor,id)
                actions = self.get_action_list(cursor,tree)
                if not self.path.exists(self.app.config['template_folder']):
                    self.mkdir(self.app.config['template_folder'])
                filename = self.path.join(self.app.config['template_folder'],\
                 f'{self.util_clean_name(list(filter(lambda x:x.parentid is None, tree))[0]["title"])}.fmea')
                while self.path.exists(filename):
                    # TODO: Find a cleaner way to ensure correct unique filename
                    filename = filename.replace('.fmea','_.fmea')
                self.export_to_file(tree,actions,filename,cursor,self.sqlite3)
                cursor.connection.close()
                return self.send_file(filename,mimetype="application/octet-stream",\
                 as_attachment=True)
            if apitype == 'report':
                # here id is the shee_id and args come in args
                report_name = self.request.args.get('name','afc')
                report_type = self.request.args.get('type','preview')
                report_opts = self.request.args.get('opts','both')
                report_data = self.report_generate(id,report_name,type=report_type,\
                 reop=[report_opts])
                if report_type == 'csv' or report_type == 'excel':
                    df = self.pd.DataFrame(data=list(l['line'] for l in \
                        report_data['lines']),columns=report_data['header'])
                    tree = self.get_sheet_tree(cursor,id)
                    if not self.path.exists(self.app.config['template_folder']):
                        self.mkdir(self.app.config['template_folder'])
                    if report_type == 'csv':
                        filename = self.path.join(self.app.config['template_folder'],\
f'{self.util_clean_name(list(filter(lambda x:x.parentid is None, tree))[0]["title"])}_{report_name}.csv')
                        df.to_csv(filename)
                    else:
                        filename = self.path.join(self.app.config['template_folder'],\
f'{self.util_clean_name(list(filter(lambda x:x.parentid is None, tree))[0]["title"])}_{report_name}.xlsx')
                        df.to_excel(filename)
                    cursor.connection.close()
                    return self.send_file(filename,mimetype="text/csv",\
                 as_attachment=True)
                report_preview = self.derive_report(report_data)
                if debug: print(f'DEBUG: Report preview - {report_preview}')
                return self.Markup(report_preview)
        if action == 'index' or action=='open':
            cursor = self.get_db_connection()
            sheets = self.get_sheets(cursor)
            if len(sheets) == 0:
                sheet_list = '<p> No sheet has been found </p>'
            else:
                sheet_list = sheets[0].__htmltable__(field_filter = lambda x:\
            x[0]=='title' or x[0]=='sheet_author' or x[0]=='sheet_created' or\
            x[0]=='asset_description', apply_to_cell=self.derive_node_as_a_for_open )
            content = sheet_list
            #print(f'DEBUG: Generated table html "{content}"')
            cursor.connection.close()
            return self.Markup(self.derive_template(content=content,\
                    header=self.derive_headers('open'),\
                    css=self.compile_css(options=['table']),js=self.compile_js()))
        if action == 'edit':
            # TODO: Implement nojs modifiers and handle state
            # TODO: Add header buttons
            cursor = self.get_db_connection()
            tree = self.get_sheet_tree(cursor,id)
            if debug: print(f'DEBUG: Editing {list(str(l) for l in tree)}')
            if debug and len(tree)>0:
                if tree[0].parentid is None:
                    print(f'DEBUG: We confirm sheet {tree[0].id}')
                else:
                    print('DEBUG: We have something else on parentid')
            actions = ''
            domain = ''
            formdata = ''
            dialog_class = 'right-dlg-hidden'
            if apitype == 'apinojs':
                dialog_class = 'right-dlg'
                formdata = ''
            actions = self.get_action_list(cursor,tree)
            domain = self.get_domain_list(cursor)
            content = f'''<div id="editor" class="editor" onscroll="scrollSync()">
            <div id="tree" class="tree">{self.derive_tree(tree,domain=domain,actions=actions)}</div>      </div>
            <div id="right-dlg" class="{dialog_class}">
             <div id="right-dlg-hdr" class="right-dlg-hdr">
              <div id="right-dlg-hdr-filler">&nbsp;</div>
              <!-- <a class="right-dlg-hdr-a" href="#" onclick="toggleBetweenClasses('act-legend','act-legend-h','act-legend');return false">
              Legend</a>&nbsp;-->
              <a class="right-dlg-hdr-a" href="#" onclick="applyClass('right-dlg',
               'right-dlg-hidden');ajaxHelperDestination('/fmea/jsapi/{id}/tree',null,'tree');return false">Hide</a>&nbsp;
             </div>
             <div id="right-dlg-content" class="right-dlg-content">
             <div id="right-dlg-pretty-bottom" class="right-dlg-ftr">&nbsp;<br/></div>
              {self.derive_action_legend(domain)}
              <h3>Action List</h3><br/>
              {self.derive_action_list(actions,domain,tree)}
              {formdata}
           <!-- TODO: Add content for all dialogs, hide contents using class -->
            <!-- </div> -->
            </div>
           </div>'''
            cursor.connection.close()
            return self.Markup(self.derive_template(content=content,\
                    header=self.derive_headers('edit',sheet_id=id),\
                    css=self.compile_css(options=['tree']),\
                    js =self.compile_js(options=['editor'])))
        if action == 'export':
            # listing of the reports with preview
            # TODO: Here we need pandas
            content = f'''<div style="width:99vw;"><a id="afc-call" href="#"
            onclick="reportView({id},'afc','preview');return false">
            Actions by failure cause (Preview)</a>&nbsp;<a id="afc-csv"
            href="/fmea/redirect/{id}/report?name=afc&type=csv">(csv)</a>&nbsp;
            <a id="afc-xlsx" href="/fmea/redirect/{id}/report?name=afc&type=excel">
            (xlsx)</a>&nbsp;<br/><div id="afc-prev" class="report-preview">
            No preview generated...</div><br/></div><br/><div style="width:99vw;">
            <a id="fmbrl-call" href="#" onclick="reportView({id},'fmbrl','preview');
            return false">Failure mode by risk level (Preview)</a>&nbsp;<a id="fmbrl-csv"
            href="/fmea/redirect/{id}/report?name=fmbrl&type=csv">(csv)</a>&nbsp;
            <a id="fmbrl-call" href="/fmea/redirect/{id}/report?name=fmbrl&type=excel">
            (xlsx)</a>&nbsp;<br/><div id="fmbrl-prev" class="report-preview">No preview
            generated...</div><br/></div><br/><div style="width:99vw;"><select
            id="aadc-opts" value="both"><option value="both" default="default">both
            </option> <option value="equipment level">equipment level</option>
            <option value="class level">class level</option></select><a id="aadc-call"
            href="#" onclick="reportView({id},'aadc','preview');return false">
            Actions at diferent criticality (Preview)</a>&nbsp;<a id="aadc-csv"
            href="#" onclick="reportView({id},'aadc','csv');return false">(csv)</a>&nbsp;
            <a id="aadc-call" href="#" onclick="reportView({id},'aadc','excel');return false">
            (xlsx)</a>&nbsp;<br/><div id="aadc-prev" class="report-preview">
            No preview generated...</div><br/></div>'''
            return self.Markup(self.derive_template(content=content,\
                    header=self.derive_headers('report',sheet_id=id),\
                    css=self.compile_css(options=['table']),\
                    js =self.compile_js(options=['report'])))
        if action == 'jsapi':
            cursor = self.get_db_connection()
            api_html = f'NOTICE: Javacript API called for id {id}'
            if apitype == 'sheetnew':
                new_id = self.util_new_node(cursor)
                cursor.connection.close()
                return self.Markup(f'/fmea/edit/{new_id}/apidefault')
            if apitype == 'tree' or apitype == 'leafupdate' or apitype == 'leafdel'\
             or apitype == 'treeact':
                # id means sheetid
                fd = self.request.form
                print(f'DEBUG: Form data object {fd}')
                leaf_to_delete = None
                target_id = None
                if fd is not None:
                    fd = fd.to_dict()
                    target_id = fd.get('id','NULL')
                    if target_id != 'NULL' and len(fd) >= 1:
                        print(f'DEBUG: Found formdata {fd}')
                        if apitype == 'leafupdate':
                            if fd.get('sheetid','NULL') == 'NULL':
                                # Function and Sheet do not have sheetid
                                anew = FMEA_Function().__nodeinband__(fd)
                                re = anew.__sqliteself__(cursor)
                                if re is None:
                                    print('WARNING: Nothing to update form db')
                                anew.__nodeinband__(fd).__sqliteupdate__(cursor)
                            else:
                                anew = FMEA_Failure_Mode().__nodeinband__(fd)
                                re = anew.__sqliteself__(cursor)
                                if re is None:
                                    print('WARNING: Nothing to update from db')
                                anew.__nodeinband__(fd).__sqliteupdate__(cursor)
                        else:
                            if apitype == 'leafdel':
                                test_table = FMEA_Function().__sqlitetable__()
                                res = cursor.execute(f'SELECT * FROM {test_table} WHERE id={id}')
                                if len(res.fetchall()) > 0:
                                    leaf_to_delete = FMEA_Function()
                                else:
                                    leaf_to_delete = FMEA_Failure_Mode()
                                leaf_to_delete.__nodeinband__({'id':target_id})
                                leaf_to_delete.__sqliteself__(cursor)
                                leaf_to_delete.__nodeinband__({'id':target_id})
                            else:
                                print(f'NOTICE: Not implemented hide of {target_id}')
                tree = self.get_sheet_tree(cursor,id)
                actions = self.get_action_list(cursor,tree)
                domain = self.get_domain_list(cursor)
                if leaf_to_delete is not None:
                    # WARNING: Ensure leaf to delete is in tree
                    print(f'DEBUG: Trying to delete {leaf_to_delete} from {list(l.id for l in tree)}')
                    leaf_to_del = list(filter(lambda x:x.id == int(leaf_to_delete.id),tree))
                    if len(leaf_to_del)>0:
                        leaf_to_delete = leaf_to_del[0]
                        tree = leaf_to_delete.delete_leaf(cursor,tree,actions)
                    else:
                        print(f'WARNING: Attempted to delete {target_id}, but not found')
                tree_query = self.request.args.to_dict(flat=False)
                api_html = self.derive_tree(tree,tree_query,actions=actions,domain=domain)
            if apitype == 'actions' or apitype == 'actionup' or\
               apitype == 'actiondel':
                # id is sheet id
                fd = self.request.form
                if fd is not None:
                    fd = fd.to_dict()
                    if fd.get('id','NULL') != 'NULL':
                        actnew = FMEA_Action().__nodeinband__(fd)
                        res = actnew.__sqliteself__(cursor)
                        res = actnew.__nodeinband__(fd).__sqliteupdate__(cursor)
                act_to_del = self.request.args.get('delact','NULL')
                if act_to_del != 'NULL':
                    if act_to_del is not None:
                        print(f'NOTICE: Attempting to delete action {act_to_del}')
                        actnew = FMEA_Action().__nodeinband__({'id':\
                                    int(act_to_del), 'parentlist': ''})
                        res = actnew.__sqliteself__(cursor)
                        tac = actnew.del_action(cursor,[],[actnew])
                    else:
                        print('ERROR: Could not recuperate node to delete')
                tree = self.get_sheet_tree(cursor,id)
                actions = self.get_action_list(cursor,tree)
                domain = self.get_domain_list(cursor)
                api_html = f'''{self.derive_action_legend(domain)}
                <h3>Action List</h3><br/>
                {self.derive_action_list(actions,domain,tree)}
                '''
            if apitype == 'leafedit' or apitype == 'leafnew' or\
                apitype == 'leafactup' or apitype == 'leafactdel' or \
                apitype == 'leafactadd':
                # for leafedit id is id, for leafnew id is parentid
                fd = self.request.form
                sheet_id = None
                if fd is not None:
                    fd = fd.to_dict()
                    if fd.get('id','NULL') != 'NULL':
                        actnew = FMEA_Action().__nodeinband__(fd)
                        res = actnew.__sqliteself__(cursor)
                        res = actnew.__nodeinband__(fd).__sqliteupdate__(cursor)
                act_to_del = self.request.args.get('delact','NULL')
                if act_to_del != 'NULL':
                    if debug: print(f'DEBUG: attempting to delete {act_to_del}')
                    actnew = FMEA_Action().__nodeinband__({'id':int(act_to_del)})
                    res = actnew.__sqliteself__(cursor)
                    if debug: print(f'DEBUG: Fetched {actnew} with result "{res}"')
                    tac = actnew.del_action(cursor,[id],[actnew])
                act_to_add = self.request.args.get('addact','NULL')
                if debug: print(f'DEBUG: Adding action {act_to_add} to leaf {str(id)}')
                if act_to_add != 'NULL':
                    actadd = FMEA_Action().__nodeinband__({'id':int(act_to_add)})
                    res = actadd.__sqliteself__(cursor)
                    if res is None: print('WARNING: Could not fetch action')
                    if actadd.parentlist == '':
                        actadd.parentlist = str(id) # we hope the node already exists
                    else:
                        actadd.parentlist = f'{actadd.parentlist},{str(id)}'
                    if debug: print(f'NOTICE: Preparing to update {str(actadd)}')
                    res = actadd.__sqliteupdate__(cursor)
                    if res is None: print(f'ERROR: Could not update {str(actadd)}')
                test_table = FMEA_Function().__sqlitetable__()
                # KNOWN-ISSUE: Here we reach with large action delete
                res = cursor.execute(f'SELECT * FROM {test_table} WHERE id={id}')
                if len(res.fetchall()) > 0:
                    leaf = FMEA_Function()
                else:
                    leaf = FMEA_Failure_Mode()
                leaf.__nodeinband__({'id':id}).__sqliteself__(cursor)
                if leaf.__nodename__() == test_table:
                    sheet_id = leaf.parentid
                else:
                    sheet_id = leaf.sheetid
                if apitype == 'leafnew':
                    new_id = self.util_new_node(cursor)
                    if leaf.parentid is None:
                        # we create a new function
                        new_leaf = FMEA_Function()
                        sheet_id = leaf.id # this will be ignored by nodeinband
                    else:
                        # we create a new failure mode
                        if leaf.__nodename__() == test_table:
                            sheet_id = leaf.parentid
                        else:
                            sheet_id = leaf.sheetid
                        new_leaf = FMEA_Failure_Mode()
                    new_leaf.__nodeinband__({'id':new_id, 'parentid':leaf.id,\
                                             'sheetid': sheet_id})
                    leaf = new_leaf
                tree = self.get_sheet_tree(cursor,sheet_id)
                api_html = self.derive_leaf_edit(cursor,leaf,tree)
            if apitype == 'actionedit' or apitype == 'actionaddnode' or\
                    apitype == 'actiondelnode':
                fd = self.request.form
                act = FMEA_Action().__nodeinband__({'id':id})
                if fd is not None:
                    fdd = fd.to_dict()
                    if len(fdd)>0:
                        act.__nodeinband__(fdd).__sqliteupdate__(cursor)
                    else:
                        act.__sqliteself__(cursor)
                else:
                    act.__sqliteself__(cursor)
                source_leaf = self.request.args.get('leafid',None)
                if source_leaf is None:
                    # TODO: detect or identify the sheet we are working on here
                    source_leaf = source_leaf
                else:
                    if apitype=='actionaddnode':
                        current_parentlist = act.parentlist.split(',')
                        current_parentlist.append(str(source_leaf))
                        act.parentlist = ','.join(list(set(current_parentlist)))
                    else:
                        if apitype=='actiondelnode':
                            current_parentlist = act.parentlist.split(',')
                            new_parentlist = list(filter(lambda x:int(x)!=source_leaf,\
                                current_parentlist))
                            act.parentlist =','.join(list(set(new_parentlist)))
                    act.__sqliteupdate__(cursor)
                api_html = self.derive_action_edit(cursor,act,id)
            if apitype == 'actionnew':
                # we might have also form data for existing node
                act = FMEA_Action()
                max_act_id = act.__sqlitenextid__(cursor)
                fd = self.request.form
                if fd is not None:
                    fdd = fd.to_dict()
                    if len(fdd)!=0 and fdd.get('id','NULL')!='NULL':
                        # we are now saving something here
                        leaf = FMEA_Failure_Mode().__nodeinband__(fdd)
                        res = leaf.__sqliteupdate__(cursor)
                        if res is None:
                            print(f'ERROR: Could not update data from {fdd}')
                    else:
                        print('NOTICE: Action new done without active form')
                if max_act_id is None:
                    max_act_id =0
                act.__nodeinband__({'id': max_act_id,'parentlist': str(id)})
                # we are not using add parent here
                api_html = self.derive_action_edit(cursor,act,id)
            cursor.connection.close()
            return api_html
        return f'NOTICE: {action} called for {id}'
    def handle_main_redirect(self,path='/',action='index',id=0,apitype='apinojs'):
        return self.redir('/fmea',code=302)
    def register_routes(self):
        # register the flask routes
        try:
            app = self.__getattribute__('app')
        except:
            script_folder = self.path.dirname(__file__)
            app = self.Flask(__name__)
            self.__setattr__('app',app)
        self.app.add_url_rule('/fmea','fmea_index',view_func=self.handle_route,\
            defaults={'action': 'index', 'id': '0','apitype': 'apidefault'},\
            methods=['GET','POST','PUT'])
        self.app.add_url_rule('/fmea/','fmea_default',view_func=self.handle_route,\
            defaults={'action': 'index', 'id': '0','apitype': 'apidefault'},\
            methods=['GET','POST','PUT'])
        self.app.add_url_rule('/fmea/<action>/<id>','fmea_action',\
            view_func=self.handle_route, defaults={'apitype': 'apidefault'},\
            methods=['GET','POST','PUT'])
        self.app.add_url_rule('/fmea/<action>/<id>/','fmea_apiroot',\
            view_func=self.handle_route, defaults={'apitype': 'apidefault'},\
            methods=['GET','POST','PUT'])
        self.app.add_url_rule('/fmea/<action>/<id>/<apitype>','fmea_api',\
            view_func=self.handle_route, methods=['GET','POST','PUT'])
        if len(list(filter(lambda x:x.endpoint == '/', self.app.url_map.iter_rules()))) == 0:
            self.app.add_url_rule('/','index_redirect',view_func=self.handle_main_redirect,\
                defaults={'action': 'index', 'id': '0','apitype': 'apidefault'},\
                methods=['GET','POST','PUT'])
    def run(self):
        # start the application
        print(list(r.endpoint for r in self.app.url_map.iter_rules()))
        self.app.debug=True
        self.app.run(host="0.0.0.0", port=5005)
    def import_from_file(self,filename,cursor,sqlite3=None,debug=False):
        # import data into table from FMEA file
        if sqlite3 is None:
            sqlite3 = self.sqlite3
        if debug: print('DEBUG IMPORT: Stage 1 - opening the file')
        newcon = sqlite3.connect(filename)
        newcur = newcon.cursor()
        bail = False
        if debug: print('DEBUG IMPORT: Stage 2 - searching the first table')
        if FMEA_Function().__sqlitecreate__(newcur).find('TABLE EXISTS')<0:
            # TODO: Leverage creation of a dict and node in band to transfer data
            # Function table is not compatible or doesn't exist
            print('ERROR: Cannot import FMEA Functions from file')
            bail = True
        if debug: print('DEBUG IMPORT: Stage 2 - searching the second table')
        if FMEA_Failure_Mode().__sqlitecreate__(newcur).find('TABLE EXISTS')<0:
            print('ERROR: Cannot import FMEA Failure Causes from file')
            bail = True
        if debug: print('DEBUG IMPORT: Stage 2 - searching the third table')
        if FMEA_Action().__sqlitecreate__(newcur).find('TABLE EXISTS')<0:
            print('ERROR')
            bail = True
        newtree = []
        if debug: print(f'DEBUG IMPORT: Stage 3 - building the structures if bail({bail}) is False')
        if bail == False:
            newtree = FMEA_Function().get_from_db(newcur,None,newtree)
            if len(newtree) >= 1:
                # we have only imported the root, let's try again
                newtree = newtree[0].get_from_db(newcur,newtree[0].id,newtree)
            # TODO: KNOWN BUG - Functions do not get imported
            if debug: print(f'''DEBUG IMPORT: Stage 4 - creating function lookup from {list(str(l) for l in newtree)}''')
            newtree = FMEA_Failure_Mode().get_from_db(newcur,None,newtree)
            newacts = FMEA_Action().get_from_db(newcur,newtree)
            newcon.close()
            if debug: print(f'''DEBUG IMPORT: Stage 4 - creating node lookup from {list(str(l) for l in newtree)}''')
            eqdi = dict()
            newtree[0].__treesort__(newtree)
            newsheetid = 0
            for leaf in newtree:
                newid = eqdi.get(int(leaf.id),int(self.util_new_node(cursor)))
                eqdi[int(leaf.id)] = newid
                if debug: print(f'DEBUG: Reasigning {str(leaf)} to id: {newid} dict size {len(eqdi)}')
                leaf.id = newid
                if leaf.parentid is not None:
                    newid = eqdi.get(int(leaf.parentid),int(self.util_new_node(cursor))+1)
                    eqdi[int(leaf.parentid)] = newid
                    leaf.parentid = newid
                else:
                    newsheetid = newid
                if leaf.__contains__('sheetid'):
                    leaf['sheetid']=newsheetid
                res = leaf.__sqliteupdate__(cursor)
                if res is None:
                    print('ERROR: Could not insert node {leaf.id}')
            if debug: print('DEBUG IMPORT: Stage 5 - creating action lookup')
            aqdi = dict()
            for act in newacts:
                newid = act.__sqlitenextid__(cursor)
                aqdi[act.id] = newid
                act.id = newid
                old_parentlist = act.parentlist
                new_parentlist = ''
                for pid in old_parentlist.split(','):
                    try:
                        if debug: print(f'''DEBUG: Attemting to attach action {act.id} to parent {pid.strip()} which has been matched to {eqdi.get(int(pid.strip()),'NOT FOUND')}''')
                        if len(new_parentlist) == 0:
                            new_parentlist = str(eqdi.get(int(pid.strip()),''))
                        else:
                            new_parentlist = f'{new_parentlist}, {eqdi.get(int(pid.strip()),"")}'
                    except Exception as e:
                        print(f'ERROR: Exception {e.__class__.__name__} saying {e.args}')
                if new_parentlist == '':
                    print('WARNING: Some orphan actions have been detected')
                act.parentlist = new_parentlist
                res = act.__sqliteupdate__(cursor)
        else:
            if debug: print('DEBUG IMPORT: Bailed - nothing happened')
            newcon.close()
        # actions can be recuperated from database
        return newtree
    def export_to_file(self,tree,actions,filename,cursor,sqlite3):
        # save current sheet into a file
        newcon = sqlite3.connect(filename)
        newcur = newcon.cursor()
        try:
            newcur = newcur.execute(FMEA_Function().__sqlitecreate__(newcur))
            newcur = newcur.execute(FMEA_Failure_Mode().__sqlitecreate__(newcur))
            newcur = newcur.execute(FMEA_Action().__sqlitecreate__(newcur))
        except Exception as e:
            print(f'''ERROR: could not create tables in export file {filename}
                Reason is {e.__class__.__name__}: {e.args}''')
        else:
            for leaf in tree:
                res = leaf.__sqliteupdate__(newcur)
            for act in actions:
                res = act.__sqliteupdate__(newcur)
            newcon.commit()
        finally:
            newcon.close()
    def app_install(self,cursor):
        # create the tables in database
        FMEA_Function().create_in_db(cursor)
        FMEA_Failure_Mode().create_in_db(cursor)
        FMEA_Action().create_in_db(cursor)
        FMEA_Domain().create_in_db(cursor)


if __name__ == '__main__':
    FMEA = FMEA_App()
    FMEA.try_imports()
    FMEA.get_secrets()
    FMEA.get_config()
    FMEA.register_routes()
    FMEA.run()